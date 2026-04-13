//! Управление криптографическими ключами ETH кошелька.

use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use coins_bip32::{
    path::DerivationPath,
    prelude::*,
};
use hmac::Hmac;
use k256::{
    ecdsa::SigningKey,
    elliptic_curve::sec1::ToEncodedPoint,
    PublicKey,
};
use pbkdf2::pbkdf2;
use pyo3::prelude::*;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use sha2::Sha256;
use tiny_bip39::{Language, Mnemonic, MnemonicType, Seed};
use tiny_keccak::{Hasher, Keccak};
use zeroize::{Zeroize, ZeroizeOnDrop, Zeroizing};

use crate::error::VaultError;

const PBKDF2_ITERATIONS: u32 = 600_000;
const PBKDF2_ITERATIONS_MIN: u32 = 600_000;
const MAX_FAILED_ATTEMPTS: u32 = 5;
const LOCKOUT_DURATION_SECS: u64 = 300;

#[derive(Serialize, Deserialize)]
struct VaultFile {
    version: u32,
    address: String,
    salt: String,
    nonce: String,
    ciphertext: String,
    iterations: u32,
    has_mnemonic: bool,
    #[serde(default)]
    created_at: u64,
}

#[derive(Serialize, Deserialize, Zeroize)]
struct VaultPayload {
    private_key: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    mnemonic: Option<String>,
}

#[derive(ZeroizeOnDrop)]
struct WalletData {
    private_key: Zeroizing<Vec<u8>>,
    address: String,
    mnemonic: Option<Zeroizing<String>>,
}

/// Преобразует &[u8] (12 байт) в Nonce без deprecated from_slice
fn bytes_to_nonce(bytes: &[u8]) -> Nonce {
    let arr: [u8; 12] = bytes.try_into().expect("nonce должен быть 12 байт");
    arr.into()
}

pub fn derive_address(private_key_bytes: &[u8]) -> Result<String, VaultError> {
    let signing_key = SigningKey::from_slice(private_key_bytes)
        .map_err(|e| VaultError::Crypto(e.to_string()))?;
    // verifying_key() возвращает VerifyingKey (не ссылку), From<&VerifyingKey> реализован
    let public_key = PublicKey::from(signing_key.verifying_key());
    let encoded = public_key.to_encoded_point(false);
    let pub_bytes = &encoded.as_bytes()[1..];
    let mut keccak = Keccak::v256();
    let mut hash = [0u8; 32];
    keccak.update(pub_bytes);
    keccak.finalize(&mut hash);
    let addr_bytes = &hash[12..];
    Ok(format!("0x{}", to_checksum_address(addr_bytes)))
}

pub fn derive_address_pub(private_key_bytes: &[u8]) -> PyResult<String> {
    derive_address(private_key_bytes).map_err(PyErr::from)
}

fn to_checksum_address(addr_bytes: &[u8]) -> String {
    let hex_addr = hex::encode(addr_bytes);
    let mut keccak = Keccak::v256();
    let mut hash = [0u8; 32];
    keccak.update(hex_addr.as_bytes());
    keccak.finalize(&mut hash);
    let hash_hex = hex::encode(hash);
    hex_addr
        .chars()
        .zip(hash_hex.chars())
        .map(|(c, h)| {
            if c.is_ascii_digit() { c }
            else if h >= '8' { c.to_ascii_uppercase() }
            else { c.to_ascii_lowercase() }
        })
        .collect()
}

fn derive_encryption_key(password: &[u8], salt: &[u8], iterations: u32) -> Zeroizing<[u8; 32]> {
    let mut key = Zeroizing::new([0u8; 32]);
    pbkdf2::<Hmac<Sha256>>(password, salt, iterations, key.as_mut_slice())
        .expect("PBKDF2 никогда не падает");
    key
}

#[pyclass(name = "KeyManager")]
pub struct PyKeyManager {
    wallet: Option<WalletData>,
    failed_attempts: u32,
    lockout_until: Option<u64>,
}

#[pymethods]
impl PyKeyManager {
    #[new]
    pub fn new() -> Self {
        Self { wallet: None, failed_attempts: 0, lockout_until: None }
    }

    pub fn generate_wallet(&mut self) -> PyResult<(String, String)> {
        let mnemonic = Mnemonic::new(MnemonicType::Words24, Language::English);
        let mnemonic_str = mnemonic.phrase().to_string();
        let seed = Seed::new(&mnemonic, "");
        let private_key_bytes = derive_eth_key_from_seed(seed.as_bytes())?;
        let address = derive_address(&private_key_bytes).map_err(PyErr::from)?;
        self.wallet = Some(WalletData {
            private_key: Zeroizing::new(private_key_bytes),
            address: address.clone(),
            mnemonic: Some(Zeroizing::new(mnemonic_str.clone())),
        });
        Ok((mnemonic_str, address))
    }

    pub fn import_from_mnemonic(&mut self, mnemonic: &str) -> PyResult<String> {
        let parsed = Mnemonic::from_phrase(mnemonic, Language::English)
            .map_err(|e| VaultError::InvalidPassword(format!("Неверная мнемоника: {e}")))?;
        let seed = Seed::new(&parsed, "");
        let private_key_bytes = derive_eth_key_from_seed(seed.as_bytes())?;
        let address = derive_address(&private_key_bytes).map_err(PyErr::from)?;
        self.wallet = Some(WalletData {
            private_key: Zeroizing::new(private_key_bytes),
            address: address.clone(),
            mnemonic: Some(Zeroizing::new(mnemonic.to_string())),
        });
        Ok(address)
    }

    pub fn import_from_private_key(&mut self, hex_key: &str) -> PyResult<String> {
        let clean = hex_key.strip_prefix("0x").unwrap_or(hex_key);
        let pk_bytes = hex::decode(clean)
            .map_err(|e| VaultError::InvalidPassword(format!("Неверный hex: {e}")))?;
        if pk_bytes.len() != 32 {
            return Err(VaultError::InvalidPassword(
                "Приватный ключ должен быть 32 байта".into(),
            ).into());
        }
        let address = derive_address(&pk_bytes).map_err(PyErr::from)?;
        self.wallet = Some(WalletData {
            private_key: Zeroizing::new(pk_bytes),
            address: address.clone(),
            mnemonic: None,
        });
        Ok(address)
    }

    pub fn encrypt_and_save(&self, password: &str, filepath: &str) -> PyResult<()> {
        let wallet = self.wallet.as_ref()
            .ok_or_else(|| VaultError::Logic("Ключ не загружен".into()))?;
        if password.is_empty() {
            return Err(VaultError::InvalidPassword("Пароль не может быть пустым".into()).into());
        }
        if password.len() < 8 {
            return Err(VaultError::InvalidPassword(
                "Пароль должен быть не менее 8 символов".into(),
            ).into());
        }

        let mut salt = [0u8; 32];
        let mut nonce_bytes = [0u8; 12];
        rand::thread_rng().fill_bytes(&mut salt);
        rand::thread_rng().fill_bytes(&mut nonce_bytes);

        let enc_key = derive_encryption_key(password.as_bytes(), &salt, PBKDF2_ITERATIONS);

        let payload = VaultPayload {
            private_key: hex::encode(wallet.private_key.as_slice()),
            mnemonic: wallet.mnemonic.as_ref().map(|m| m.as_str().to_string()),
        };
        let mut plaintext = Zeroizing::new(
            serde_json::to_vec(&payload)
                .map_err(|e| VaultError::Logic(format!("JSON: {e}")))?,
        );

        let cipher = Aes256Gcm::new_from_slice(enc_key.as_slice())
            .map_err(|e| VaultError::Crypto(e.to_string()))?;
        let nonce = bytes_to_nonce(&nonce_bytes);
        let aad_str = wallet.address.to_lowercase();
        let aad = aad_str.as_bytes();
        let ciphertext = cipher
            .encrypt(&nonce, aes_gcm::aead::Payload { msg: &plaintext, aad })
            .map_err(|e| VaultError::Crypto(e.to_string()))?;

        plaintext.zeroize();

        let created_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let vault = VaultFile {
            version: 1,
            address: wallet.address.clone(),
            salt: hex::encode(salt),
            nonce: hex::encode(nonce_bytes),
            ciphertext: hex::encode(&ciphertext),
            iterations: PBKDF2_ITERATIONS,
            has_mnemonic: wallet.mnemonic.is_some(),
            created_at,
        };

        let tmp_path = format!("{filepath}.tmp");
        let json = serde_json::to_string_pretty(&vault)
            .map_err(|e| VaultError::Logic(format!("JSON: {e}")))?;
        let write_result = fs::write(&tmp_path, &json)
            .and_then(|_| fs::rename(&tmp_path, filepath));
        if let Err(e) = write_result {
            let _ = fs::remove_file(&tmp_path);
            return Err(VaultError::Io(e).into());
        }
        Ok(())
    }

    pub fn decrypt_and_load(&mut self, password: &str, filepath: &str) -> PyResult<String> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        if let Some(until) = self.lockout_until {
            if now < until {
                let wait = until - now;
                return Err(pyo3::exceptions::PyPermissionError::new_err(
                    format!("Блокировка. Подождите {wait} сек.")
                ));
            } else {
                self.lockout_until = None;
                self.failed_attempts = 0;
            }
        }
        if self.failed_attempts >= MAX_FAILED_ATTEMPTS {
            self.lockout_until = Some(now + LOCKOUT_DURATION_SECS);
            return Err(pyo3::exceptions::PyPermissionError::new_err(
                format!("Блокировка на {} сек. Подождите.", LOCKOUT_DURATION_SECS)
            ));
        }

        let canon = std::path::Path::new(filepath)
            .canonicalize()
            .map_err(VaultError::Io)?;
        if canon.is_symlink() {
            return Err(VaultError::PathTraversal(
                "Симлинки на vault-файл запрещены".into(),
            ).into());
        }

        let json_str = fs::read_to_string(&canon).map_err(VaultError::Io)?;
        let vault: VaultFile = serde_json::from_str(&json_str)
            .map_err(|e| VaultError::Logic(format!("Неверный формат vault: {e}")))?;

        if vault.version != 1 {
            return Err(VaultError::Logic("Неподдерживаемая версия vault".into()).into());
        }

        let salt = hex::decode(&vault.salt)
            .map_err(|_| VaultError::Logic("Неверный salt hex".into()))?;
        let nonce_bytes = hex::decode(&vault.nonce)
            .map_err(|_| VaultError::Logic("Неверный nonce hex".into()))?;
        let ciphertext = hex::decode(&vault.ciphertext)
            .map_err(|_| VaultError::Logic("Неверный ciphertext hex".into()))?;

        let iterations = std::cmp::max(vault.iterations, PBKDF2_ITERATIONS_MIN);
        let enc_key = derive_encryption_key(password.as_bytes(), &salt, iterations);

        let cipher = Aes256Gcm::new_from_slice(enc_key.as_slice())
            .map_err(|e| VaultError::Crypto(e.to_string()))?;
        let nonce = bytes_to_nonce(&nonce_bytes);
        let aad_str = vault.address.to_lowercase();
        let aad = aad_str.as_bytes();

        let plaintext_result = cipher.decrypt(
            &nonce,
            aes_gcm::aead::Payload { msg: &ciphertext, aad },
        );

        let plaintext_bytes = match plaintext_result {
            Ok(b) => b,
            Err(_) => {
                self.failed_attempts += 1;
                if self.failed_attempts >= MAX_FAILED_ATTEMPTS {
                    self.lockout_until = Some(now + LOCKOUT_DURATION_SECS);
                }
                let remaining = MAX_FAILED_ATTEMPTS.saturating_sub(self.failed_attempts);
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "Неверный пароль. Осталось попыток: {remaining}"
                )));
            }
        };
        let mut plaintext = Zeroizing::new(plaintext_bytes);

        let payload: VaultPayload = serde_json::from_slice(&plaintext)
            .map_err(|e| VaultError::Logic(format!("Payload JSON: {e}")))?;

        let pk_bytes = hex::decode(&payload.private_key)
            .map_err(|_| VaultError::Logic("Неверный hex ключа".into()))?;

        let derived_addr = derive_address(&pk_bytes).map_err(PyErr::from)?;
        if derived_addr.to_lowercase() != vault.address.to_lowercase() {
            self.wallet = None;
            return Err(VaultError::Logic(
                "Ошибка целостности: адрес не совпадает с ключом".into(),
            ).into());
        }

        plaintext.zeroize();

        self.wallet = Some(WalletData {
            private_key: Zeroizing::new(pk_bytes),
            address: vault.address.clone(),
            mnemonic: payload.mnemonic.map(Zeroizing::new),
        });
        self.failed_attempts = 0;
        self.lockout_until = None;
        Ok(vault.address)
    }

    pub fn get_private_key<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
        let wallet = self.wallet.as_ref()
            .ok_or_else(|| VaultError::Logic("Ключ не загружен".into()))?;
        Ok(pyo3::types::PyBytes::new_bound(py, &wallet.private_key))
    }

    #[getter]
    pub fn address(&self) -> Option<String> {
        self.wallet.as_ref().map(|w| w.address.clone())
    }

    #[getter]
    pub fn mnemonic(&self) -> Option<String> {
        self.wallet.as_ref()
            .and_then(|w| w.mnemonic.as_ref().map(|m| m.as_str().to_string()))
    }

    #[getter]
    pub fn remaining_attempts(&self) -> u32 {
        MAX_FAILED_ATTEMPTS.saturating_sub(self.failed_attempts)
    }

    #[getter]
    pub fn lockout_seconds_remaining(&self) -> Option<u64> {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        self.lockout_until.and_then(|until| {
            if until > now { Some(until - now) } else { None }
        })
    }

    pub fn clear(&mut self) {
        self.wallet = None;
        self.failed_attempts = 0;
        self.lockout_until = None;
    }
}

fn derive_eth_key_from_seed(seed: &[u8]) -> PyResult<Vec<u8>> {
    let master = coins_bip32::xkeys::XPriv::root_from_seed(seed, None)
        .map_err(|e| VaultError::Crypto(format!("BIP32: {e}")))?;
    let path: DerivationPath = "m/44'/60'/0'/0/0"
        .parse()
        .map_err(|e| VaultError::Crypto(format!("Путь: {e}")))?;
    let child = master.derive_path(&path)
        .map_err(|e| VaultError::Crypto(format!("HD: {e}")))?;
    // coins-bip32 0.13: XPriv реализует AsRef<SigningKey>
    let signing_key: &k256::ecdsa::SigningKey = child.as_ref();
    Ok(signing_key.to_bytes().to_vec())
}
