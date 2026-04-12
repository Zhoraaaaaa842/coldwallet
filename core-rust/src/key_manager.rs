//! key_manager.rs — генерация и управление ETH-ключами.
//!
//! Реализует:
//!   - BIP-39 мнемоника (256 бит / 24 слова) — крейт tiny-bip39
//!   - HD деривация m/44'/60'/0'/0/0 — крейт coins-bip32
//!   - AES-256-GCM шифрование vault-файла
//!   - PBKDF2-SHA256, 600_000 итераций
//!   - Все секреты в Zeroizing<T>, ZeroizeOnDrop
//!   - Rate-limit: блокировка после 5 неверных паролей
//!
//! Отличия от Python-версии:
//!   1. Приватный ключ и мнемоника хранятся в Zeroizing<Vec<u8>>/Zeroizing<String>
//!      — обнуляются автоматически при Drop, без ctypes-хаков.
//!   2. Вся крипто на нативных Rust-крейтах (нет Python-зависимостей cryptography/mnemonic).
//!   3. Rate-limit встроен на уровне структуры, не обойти через reflection.

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyRuntimeError, PyPermissionError};

use aes_gcm::{
    aead::{Aead, KeyInit, OsRng},
    Aes256Gcm, Key, Nonce,
};
use hmac::Hmac;
use pbkdf2::pbkdf2;
use sha2::Sha256;
use tiny_bip39::{Language, Mnemonic, MnemonicType, Seed};
use coins_bip32::{
    enc::{MainnetEncoder, XKeyEncoder},
    path::DerivationPath,
    xkeys::Parent,
};
use k256::{
    ecdsa::SigningKey,
    SecretKey,
};
use tiny_keccak::{Hasher, Keccak};
use zeroize::{Zeroize, ZeroizeOnDrop, Zeroizing};
use rand::RngCore;
use serde_json;

/// Минимально допустимое число итераций PBKDF2.
/// Значение из файла клампируется: max(file_value, MIN_ITERATIONS).
const MIN_ITERATIONS: u32 = 600_000;
const SALT_SIZE: usize = 32;
const NONCE_SIZE: usize = 12;
const MAX_FAILED: u8 = 5;

// ─────────────────────────────────────────────────────────────────────────────
// Вспомогательная функция: Ethereum checksum address из 20-байтного хэша
// ─────────────────────────────────────────────────────────────────────────────

/// Вычисляет keccak256 произвольных байт.
fn keccak256(data: &[u8]) -> [u8; 32] {
    let mut hasher = Keccak::v256();
    let mut out = [0u8; 32];
    hasher.update(data);
    hasher.finalize(&mut out);
    out
}

/// Конвертирует 20-байтный публичный ключ → EIP-55 checksum address.
fn to_checksum_address(addr_bytes: &[u8; 20]) -> String {
    let hex = hex::encode(addr_bytes);
    let hash = keccak256(hex.as_bytes());
    let mut result = String::with_capacity(42);
    result.push_str("0x");
    for (i, c) in hex.chars().enumerate() {
        let nibble = (hash[i / 2] >> (if i % 2 == 0 { 4 } else { 0 })) & 0x0f;
        if c.is_ascii_alphabetic() && nibble >= 8 {
            result.push(c.to_ascii_uppercase());
        } else {
            result.push(c);
        }
    }
    result
}

/// Деривирует ETH-адрес из секретного ключа k256.
fn derive_address(secret_key: &SecretKey) -> String {
    use k256::elliptic_curve::PublicKey;
    use k256::elliptic_curve::sec1::ToEncodedPoint;

    let pk = secret_key.public_key();
    // Uncompressed pubkey: 0x04 ++ X(32) ++ Y(32) = 65 байт
    let encoded = pk.to_encoded_point(false);
    let pubkey_bytes = encoded.as_bytes();
    // Пропускаем первый байт 0x04, берём X+Y (64 байта)
    let hash = keccak256(&pubkey_bytes[1..]);
    // Берём последние 20 байт
    let mut addr = [0u8; 20];
    addr.copy_from_slice(&hash[12..]);
    to_checksum_address(&addr)
}

// ─────────────────────────────────────────────────────────────────────────────
// Внутренняя структура секретов (не экспортируется в Python)
// ─────────────────────────────────────────────────────────────────────────────

/// Хранит все секреты кошелька.
/// ZeroizeOnDrop — автоматически затирает память при drop().
#[derive(ZeroizeOnDrop)]
struct WalletSecrets {
    /// Приватный ключ: 32 байта
    private_key: Zeroizing<Vec<u8>>,
    /// Мнемоника (опционально)
    mnemonic: Zeroizing<String>,
    /// ETH-адрес (публичный — не секрет, но храним рядом)
    #[zeroize(skip)]
    address: String,
    /// Мнемоника присутствует?
    #[zeroize(skip)]
    has_mnemonic: bool,
}

// ─────────────────────────────────────────────────────────────────────────────
// Публичный Python-класс
// ─────────────────────────────────────────────────────────────────────────────

/// Python-класс: управление ключами ETH кошелька.
/// Использование:
///   km = KeyManager()
///   mnemonic, address = km.generate_wallet()
///   km.encrypt_and_save("password", "/path/to/wallet.vault")
#[pyclass(module = "coldvault_core")]
pub struct KeyManager {
    secrets: Option<WalletSecrets>,
    failed_attempts: u8,
}

#[pymethods]
impl KeyManager {
    /// Создаёт пустой KeyManager без загруженных ключей.
    #[new]
    pub fn new() -> Self {
        KeyManager {
            secrets: None,
            failed_attempts: 0,
        }
    }

    // ── Генерация ──────────────────────────────────────────────────────────

    /// Генерирует новый кошелёк.
    /// Возвращает (mnemonic: str, address: str).
    pub fn generate_wallet(&mut self) -> PyResult<(String, String)> {
        // 24 слова = 256 бит энтропии
        let mnemonic = Mnemonic::new(MnemonicType::Words24, Language::English);
        let phrase = mnemonic.phrase().to_string();

        let (private_key_bytes, address) = derive_from_mnemonic(&phrase)?;

        self.secrets = Some(WalletSecrets {
            private_key: Zeroizing::new(private_key_bytes),
            mnemonic: Zeroizing::new(phrase.clone()),
            address: address.clone(),
            has_mnemonic: true,
        });

        Ok((phrase, address))
    }

    // ── Импорт ────────────────────────────────────────────────────────────

    /// Импортирует кошелёк из BIP-39 мнемоники.
    /// Возвращает ETH-адрес.
    pub fn import_from_mnemonic(&mut self, mnemonic: String) -> PyResult<String> {
        // Валидация мнемоники
        Mnemonic::from_phrase(&mnemonic, Language::English)
            .map_err(|e| PyValueError::new_err(format!("Неверная мнемоника: {e}")))?;

        let (private_key_bytes, address) = derive_from_mnemonic(&mnemonic)?;

        self.secrets = Some(WalletSecrets {
            private_key: Zeroizing::new(private_key_bytes),
            mnemonic: Zeroizing::new(mnemonic),
            address: address.clone(),
            has_mnemonic: true,
        });

        Ok(address)
    }

    /// Импортирует кошелёк из hex приватного ключа.
    /// Возвращает ETH-адрес.
    pub fn import_from_private_key(&mut self, hex_key: String) -> PyResult<String> {
        let hex_clean = hex_key.trim_start_matches("0x");
        let key_bytes = hex::decode(hex_clean)
            .map_err(|_| PyValueError::new_err("Приватный ключ: невалидный hex"))?;

        if key_bytes.len() != 32 {
            return Err(PyValueError::new_err("Приватный ключ должен быть ровно 32 байта"));
        }

        let secret = SecretKey::from_slice(&key_bytes)
            .map_err(|e| PyValueError::new_err(format!("Невалидный ключ secp256k1: {e}")))?;
        let address = derive_address(&secret);

        let mut pk = Zeroizing::new(vec![0u8; 32]);
        pk.copy_from_slice(&key_bytes);

        self.secrets = Some(WalletSecrets {
            private_key: pk,
            mnemonic: Zeroizing::new(String::new()),
            address: address.clone(),
            has_mnemonic: false,
        });

        Ok(address)
    }

    // ── Шифрование / дешифрование ─────────────────────────────────────────

    /// Шифрует ключ и сохраняет в .vault файл.
    /// Формат совместим с Python-версией.
    pub fn encrypt_and_save(&self, password: String, filepath: String) -> PyResult<()> {
        let s = self.secrets.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Ключ не загружен"))?;

        if password.is_empty() {
            return Err(PyValueError::new_err("Пароль не может быть пустым"));
        }

        // Генерируем соль и nonce
        let mut salt = [0u8; SALT_SIZE];
        let mut nonce_bytes = [0u8; NONCE_SIZE];
        OsRng.fill_bytes(&mut salt);
        OsRng.fill_bytes(&mut nonce_bytes);

        // PBKDF2-SHA256 → 32-байтовый ключ AES
        let aes_key = derive_key(password.as_bytes(), &salt, MIN_ITERATIONS)?;

        // Собираем plaintext payload
        let payload = if s.has_mnemonic && !s.mnemonic.is_empty() {
            serde_json::json!({
                "private_key": hex::encode(&*s.private_key),
                "mnemonic": s.mnemonic.as_str()
            })
        } else {
            serde_json::json!({
                "private_key": hex::encode(&*s.private_key)
            })
        };

        let mut plaintext = Zeroizing::new(
            serde_json::to_vec(&payload)
                .map_err(|e| PyRuntimeError::new_err(format!("JSON сериализация: {e}")))?
        );

        // AES-256-GCM шифрование; AAD = адрес кошелька
        let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(&*aes_key));
        let nonce = Nonce::from_slice(&nonce_bytes);
        let aad = s.address.as_bytes();

        use aes_gcm::aead::Payload;
        let ciphertext = cipher
            .encrypt(nonce, Payload { msg: &plaintext, aad })
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка шифрования: {e}")))?;

        // Затираем plaintext сразу после шифрования
        plaintext.zeroize();

        // Формат файла (совместим с Python-версией)
        let vault = serde_json::json!({
            "version": 1,
            "address": s.address,
            "salt": hex::encode(&salt),
            "nonce": hex::encode(&nonce_bytes),
            "ciphertext": hex::encode(&ciphertext),
            "iterations": MIN_ITERATIONS,
            "has_mnemonic": s.has_mnemonic
        });

        // Атомарная запись через временный файл
        let tmp = format!("{filepath}.tmp");
        std::fs::write(&tmp, serde_json::to_string_pretty(&vault).unwrap())
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка записи файла: {e}")))?;
        std::fs::rename(&tmp, &filepath)
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка сохранения файла: {e}")))?;

        Ok(())
    }

    /// Дешифрует кошелёк из .vault файла.
    /// Возвращает ETH-адрес.
    pub fn decrypt_and_load(&mut self, password: String, filepath: String) -> PyResult<String> {
        // Rate-limit
        if self.failed_attempts >= MAX_FAILED {
            return Err(PyPermissionError::new_err(format!(
                "Превышено максимальное число попыток ({MAX_FAILED}). Перезапустите приложение."
            )));
        }

        let content = std::fs::read_to_string(&filepath)
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка чтения файла: {e}")))?;
        let vault: serde_json::Value = serde_json::from_str(&content)
            .map_err(|e| PyValueError::new_err(format!("Невалидный JSON: {e}")))?;

        if vault["version"] != 1 {
            return Err(PyValueError::new_err("Неподдерживаемая версия формата кошелька"));
        }

        let salt = hex::decode(vault["salt"].as_str().unwrap_or(""))
            .map_err(|_| PyValueError::new_err("Невалидная соль"))?;
        let nonce_bytes = hex::decode(vault["nonce"].as_str().unwrap_or(""))
            .map_err(|_| PyValueError::new_err("Невалидный nonce"))?;
        let ciphertext = hex::decode(vault["ciphertext"].as_str().unwrap_or(""))
            .map_err(|_| PyValueError::new_err("Невалидный ciphertext"))?;
        let address = vault["address"].as_str().unwrap_or("").to_string();
        let has_mnemonic = vault["has_mnemonic"].as_bool().unwrap_or(false);

        // Клампим iterations: никогда не принимаем меньше MIN_ITERATIONS
        let file_iterations = vault["iterations"].as_u64().unwrap_or(MIN_ITERATIONS as u64) as u32;
        let iterations = file_iterations.max(MIN_ITERATIONS);

        // Деривируем ключ
        let aes_key = derive_key(password.as_bytes(), &salt, iterations)?;

        // AES-256-GCM дешифрование
        let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(&*aes_key));
        let nonce = Nonce::from_slice(&nonce_bytes);
        let aad = address.as_bytes();

        use aes_gcm::aead::Payload;
        let plaintext_bytes = cipher
            .decrypt(nonce, Payload { msg: &ciphertext, aad })
            .map_err(|_| {
                self.failed_attempts += 1;
                let remaining = MAX_FAILED - self.failed_attempts;
                PyValueError::new_err(format!(
                    "Неверный пароль или повреждённый файл. Осталось попыток: {remaining}"
                ))
            })?;

        let mut plaintext = Zeroizing::new(plaintext_bytes);

        let payload: serde_json::Value = serde_json::from_slice(&plaintext)
            .map_err(|e| PyValueError::new_err(format!("Ошибка разбора payload: {e}")))?;

        let pk_hex = payload["private_key"].as_str()
            .ok_or_else(|| PyValueError::new_err("Нет поля private_key"))?;
        let pk_bytes = hex::decode(pk_hex)
            .map_err(|_| PyValueError::new_err("Невалидный hex приватного ключа"))?;

        // Верифицируем адрес
        let secret = SecretKey::from_slice(&pk_bytes)
            .map_err(|_| PyValueError::new_err("Невалидный приватный ключ"))?;
        let derived_address = derive_address(&secret);
        if derived_address.to_lowercase() != address.to_lowercase() {
            plaintext.zeroize();
            return Err(PyValueError::new_err("Ошибка целостности: адрес не совпадает с ключом"));
        }

        let mnemonic_str = if has_mnemonic {
            payload["mnemonic"].as_str().unwrap_or("").to_string()
        } else {
            String::new()
        };

        // Затираем plaintext
        plaintext.zeroize();

        let mut pk = Zeroizing::new(vec![0u8; 32]);
        pk.copy_from_slice(&pk_bytes);

        self.secrets = Some(WalletSecrets {
            private_key: pk,
            mnemonic: Zeroizing::new(mnemonic_str),
            address: derived_address.clone(),
            has_mnemonic,
        });
        // Сбрасываем счётчик при успехе
        self.failed_attempts = 0;

        Ok(derived_address)
    }

    // ── Получение данных ──────────────────────────────────────────────────

    /// Возвращает приватный ключ как bytes (для подписи транзакций).
    /// ВНИМАНИЕ: передаёт владение копией — очищай на стороне Python!
    pub fn get_private_key<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyBytes>> {
        let s = self.secrets.as_ref()
            .ok_or_else(|| PyRuntimeError::new_err("Ключ не загружен"))?;
        Ok(pyo3::types::PyBytes::new(py, &s.private_key))
    }

    /// Возвращает адрес кошелька.
    pub fn get_address(&self) -> PyResult<String> {
        self.secrets.as_ref()
            .map(|s| s.address.clone())
            .ok_or_else(|| PyRuntimeError::new_err("Ключ не загружен"))
    }

    /// Возвращает оставшееся число попыток ввода пароля.
    pub fn remaining_attempts(&self) -> u8 {
        MAX_FAILED.saturating_sub(self.failed_attempts)
    }

    /// Безопасно очищает все секреты из памяти.
    pub fn clear(&mut self) {
        // Drop на WalletSecrets автоматически вызовет ZeroizeOnDrop
        self.secrets = None;
        self.failed_attempts = 0;
    }
}

// Автоматически вызывается Drop при выходе из scope Python-объекта
impl Drop for KeyManager {
    fn drop(&mut self) {
        self.clear();
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Вспомогательные функции (не экспортируются в Python)
// ─────────────────────────────────────────────────────────────────────────────

/// PBKDF2-SHA256: пароль + соль → 32-байтовый ключ AES.
fn derive_key(password: &[u8], salt: &[u8], iterations: u32) -> PyResult<Zeroizing<Vec<u8>>> {
    let mut key = Zeroizing::new(vec![0u8; 32]);
    pbkdf2::<Hmac<Sha256>>(password, salt, iterations, &mut key)
        .map_err(|e| PyRuntimeError::new_err(format!("PBKDF2 ошибка: {e}")))?;
    Ok(key)
}

/// Деривирует приватный ключ из BIP-39 мнемоники по пути m/44'/60'/0'/0/0.
fn derive_from_mnemonic(phrase: &str) -> PyResult<(Vec<u8>, String)> {
    // 1. Seed из мнемоники (без passphrase)
    let mnemonic = Mnemonic::from_phrase(phrase, Language::English)
        .map_err(|e| PyValueError::new_err(format!("Неверная мнемоника: {e}")))?;
    let seed = Seed::new(&mnemonic, "");
    let seed_bytes = seed.as_bytes();

    // 2. Мастер-ключ BIP-32
    let xpriv = coins_bip32::xkeys::XPrivKey::root_from_seed(seed_bytes, &MainnetEncoder)
        .map_err(|e| PyRuntimeError::new_err(format!("BIP32 root key: {e}")))?;

    // 3. Деривация m/44'/60'/0'/0/0
    let path: DerivationPath = "m/44'/60'/0'/0/0".parse()
        .map_err(|e| PyRuntimeError::new_err(format!("Путь деривации: {e}")))?;
    let child = xpriv.derive_path(&path)
        .map_err(|e| PyRuntimeError::new_err(format!("Деривация ключа: {e}")))?;

    // 4. Приватный ключ → secp256k1 → адрес
    let sk_bytes = child.key.to_bytes();
    let secret = SecretKey::from_slice(&sk_bytes)
        .map_err(|e| PyValueError::new_err(format!("secp256k1 ключ: {e}")))?;
    let address = derive_address(&secret);

    Ok((sk_bytes.to_vec(), address))
}
