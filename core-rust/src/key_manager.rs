//! Управление криптографическими ключами ETH кошелька.
//!
//! Безопасность памяти:
//!   - Приватный ключ и мнемоника хранятся в Zeroizing<Vec<u8>> / Zeroizing<String>
//!   - ZeroizeOnDrop гарантирует затирание при drop()
//!   - Промежуточные буферы шифрования затираются явно

use std::fs;

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

/// Количество итераций PBKDF2 (OWASP 2024 рекомендация)
const PBKDF2_ITERATIONS: u32 = 600_000;
/// Минимально допустимое значение итераций из vault-файла
const PBKDF2_ITERATIONS_MIN: u32 = 600_000;
/// Количество неверных попыток до блокировки
const MAX_FAILED_ATTEMPTS: u32 = 5;

/// Формат JSON vault-файла (совместим с Python-версией)
#[derive(Serialize, Deserialize)]
struct VaultFile {
    version: u32,
    address: String,
    salt: String,
    nonce: String,
    ciphertext: String,
    iterations: u32,
    has_mnemonic: bool,
}

/// Содержимое зашифрованного plaintext (внутри AES-GCM)
#[derive(Serialize, Deserialize, Zeroize)]
struct VaultPayload {
    private_key: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    mnemonic: Option<String>,
}

/// Внутренние данные кошелька — все секреты в Zeroizing<T>
#[derive(ZeroizeOnDrop)]
struct WalletData {
    /// 32-байтный приватный ключ secp256k1
    private_key: Zeroizing<Vec<u8>>,
    /// ETH-адрес (0x...)
    address: String,
    /// BIP-39 мнемоника (24 слова), если есть
    mnemonic: Option<Zeroizing<String>>,
}

/// Деривирует ETH-адрес из приватного ключа через keccak256.
/// BUG FIX: была приватной — нужна в transaction.rs для get_address()
pub fn derive_address(private_key_bytes: &[u8]) -> Result<String, VaultError> {
    let signing_key = SigningKey::from_slice(private_key_bytes)
        .map_err(|e| VaultError::Crypto(e.to_string()))?;
    let public_key = PublicKey::from(&signing_key.verifying_key());
    // Uncompressed точка без префикса 0x04 (64 байта)
    let encoded = public_key.to_encoded_point(false);
    let pub_bytes = &encoded.as_bytes()[1..];
    let mut keccak = Keccak::v256();
    let mut hash = [0u8; 32];
    keccak.update(pub_bytes);
    keccak.finalize(&mut hash);
    let addr_bytes = &hash[12..];
    Ok(format!("0x{}", to_checksum_address(addr_bytes)))
}

/// Публичная обёртка для transaction.rs — возвращает PyResult.
pub fn derive_address_pub(private_key_bytes: &[u8]) -> PyResult<String> {
    derive_address(private_key_bytes).map_err(PyErr::from)
}

/// EIP-55: checksum-адрес через keccak256 hex-строки адреса.
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
            if c.is_ascii_digit() {
                c
            } else if h >= '8' {
                c.to_ascii_uppercase()
            } else {
                c.to_ascii_lowercase()
            }
        })
        .collect::<String>()
}

/// Деривирует AES-ключ из пароля через PBKDF2-SHA256.
/// Результат — Zeroizing<[u8; 32]> для автоматического затирания.
fn derive_encryption_key(
    password: &[u8],
    salt: &[u8],
    iterations: u32,
) -> Zeroizing<[u8; 32]> {
    let mut key = Zeroizing::new([0u8; 32]);
    pbkdf2::<Hmac<Sha256>>(password, salt, iterations, key.as_mut_slice())
        .expect("PBKDF2 никогда не падает с корректными параметрами");
    key
}

/// Python-класс KeyManager.
#[pyclass(name = "KeyManager")]
pub struct PyKeyManager {
    wallet: Option<WalletData>,
    failed_attempts: u32,
}

#[pymethods]
impl PyKeyManager {
    #[new]
    pub fn new() -> Self {
        Self { wallet: None, failed_attempts: 0 }
    }

    /// Генерирует новый ETH-кошелёк (BIP-39, 256 бит = 24 слова).
    /// Возвращает (mnemonic: str, address: str).
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

    /// Импортирует кошелёк из BIP-39 мнемоники. Возвращает ETH-адрес.
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

    /// Импортирует кошелёк из hex-строки приватного ключа (с 0x или без).
    /// Возвращает ETH-адрес.
    pub fn import_from_private_key(&mut self, hex_key: &str) -> PyResult<String> {
        let clean = hex_key.strip_prefix("0x").unwrap_or(hex_key);
        let pk_bytes = hex::decode(clean)
            .map_err(|e| VaultError::InvalidPassword(format!("Неверный hex: {e}")))?;
        if pk_bytes.len() != 32 {
            return Err(VaultError::InvalidPassword(
                "Приватный ключ должен быть 32 байта (64 hex-символа)".into(),
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

    /// Шифрует приватный ключ через AES-256-GCM + PBKDF2 и сохраняет в .vault файл.
    pub fn encrypt_and_save(&self, password: &str, filepath: &str) -> PyResult<()> {
        let wallet = self.wallet.as_ref()
            .ok_or_else(|| VaultError::Logic("Ключ не загружен".into()))?;
        if password.is_empty() {
            return Err(VaultError::InvalidPassword("Пароль не может быть пустым".into()).into());
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
                .map_err(|e| VaultError::Logic(format!("JSON сериализация: {e}")))?,
        );

        let cipher = Aes256Gcm::new_from_slice(enc_key.as_slice())
            .map_err(|e| VaultError::Crypto(e.to_string()))?;
        let nonce = Nonce::from_slice(&nonce_bytes);
        let aad = wallet.address.as_bytes();
        let ciphertext = cipher
            .encrypt(nonce, aes_gcm::aead::Payload { msg: &plaintext, aad })
            .map_err(|e| VaultError::Crypto(e.to_string()))?;

        plaintext.zeroize();

        let vault = VaultFile {
            version: 1,
            address: wallet.address.clone(),
            salt: hex::encode(salt),
            nonce: hex::encode(nonce_bytes),
            ciphertext: hex::encode(&ciphertext),
            iterations: PBKDF2_ITERATIONS,
            has_mnemonic: wallet.mnemonic.is_some(),
        };

        let tmp_path = format!("{filepath}.tmp");
        let json = serde_json::to_string_pretty(&vault)
            .map_err(|e| VaultError::Logic(format!("JSON: {e}")))?;
        fs::write(&tmp_path, &json).map_err(VaultError::Io)?;
        fs::rename(&tmp_path, filepath).map_err(VaultError::Io)?;
        Ok(())
    }

    /// Загружает и дешифрует кошелёк из .vault файла.
    /// Блокирует после MAX_FAILED_ATTEMPTS неверных паролей.
    /// Возвращает ETH-адрес.
    pub fn decrypt_and_load(&mut self, password: &str, filepath: &str) -> PyResult<String> {
        if self.failed_attempts >= MAX_FAILED_ATTEMPTS {
            return Err(VaultError::TooManyAttempts.into());
        }

        let json_str = fs::read_to_string(filepath).map_err(VaultError::Io)?;
        let vault: VaultFile = serde_json::from_str(&json_str)
            .map_err(|e| VaultError::Logic(format!("Неверный формат vault: {e}")))?;

        if vault.version != 1 {
            return Err(VaultError::Logic("Неподдерживаемая версия vault-файла".into()).into());
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
        let nonce = Nonce::from_slice(&nonce_bytes);
        let aad = vault.address.as_bytes();

        let plaintext_bytes = cipher
            .decrypt(nonce, aes_gcm::aead::Payload { msg: &ciphertext, aad })
            .map_err(|_| {
                self.failed_attempts += 1;
                let remaining = MAX_FAILED_ATTEMPTS.saturating_sub(self.failed_attempts);
                VaultError::InvalidPassword(format!(
                    "Неверный пароль или повреждённый файл. Осталось попыток: {remaining}"
                ))
            });
        let plaintext_bytes = plaintext_bytes?;
        let mut plaintext = Zeroizing::new(plaintext_bytes);

        let payload: VaultPayload = serde_json::from_slice(&plaintext)
            .map_err(|e| VaultError::Logic(format!("Payload JSON: {e}")))?;

        let pk_bytes = hex::decode(&payload.private_key)
            .map_err(|_| VaultError::Logic("Неверный hex приватного ключа".into()))?;

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
        Ok(vault.address)
    }

    /// Возвращает приватный ключ как bytes (для подписи транзакций).
    pub fn get_private_key<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
        let wallet = self.wallet.as_ref()
            .ok_or_else(|| VaultError::Logic("Ключ не загружен".into()))?;
        Ok(pyo3::types::PyBytes::new_bound(py, &wallet.private_key))
    }

    /// ETH-адрес или None если кошелёк не загружен.
    #[getter]
    pub fn address(&self) -> Option<String> {
        self.wallet.as_ref().map(|w| w.address.clone())
    }

    /// Мнемоника или None.
    #[getter]
    pub fn mnemonic(&self) -> Option<String> {
        self.wallet.as_ref()
            .and_then(|w| w.mnemonic.as_ref().map(|m| m.as_str().to_string()))
    }

    /// Число оставшихся попыток ввода пароля.
    #[getter]
    pub fn remaining_attempts(&self) -> u32 {
        MAX_FAILED_ATTEMPTS.saturating_sub(self.failed_attempts)
    }

    /// Безопасно затирает все секретные данные из памяти.
    pub fn clear(&mut self) {
        self.wallet = None;
        self.failed_attempts = 0;
    }
}

/// Деривация ETH-ключа из BIP-39 seed по пути m/44'/60'/0'/0/0.
fn derive_eth_key_from_seed(seed: &[u8]) -> PyResult<Vec<u8>> {
    let master = coins_bip32::xkeys::XPriv::root_from_seed(seed, None)
        .map_err(|e| VaultError::Crypto(format!("BIP32 master key: {e}")))?;
    let path: DerivationPath = "m/44'/60'/0'/0/0"
        .parse()
        .map_err(|e| VaultError::Crypto(format!("Путь деривации: {e}")))?;
    let child = master.derive_path(&path)
        .map_err(|e| VaultError::Crypto(format!("HD деривация: {e}")))?;
    Ok(child.private_key().to_bytes().to_vec())
}
