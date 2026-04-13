use aes_gcm::{Aes256Gcm, KeyInit, AeadCore};
use aes_gcm::aead::Aead;
use aes_gcm::aead::generic_array::GenericArray;
use pbkdf2::pbkdf2_hmac;
use sha2::Sha256;
use bip39::{Mnemonic, Language};
use hex;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};

const VAULT_VERSION: u8 = 2;
const ITERATIONS: u32 = 1_000_000; // Increased from 600k for better security
const SALT_SIZE: usize = 32;

#[derive(Serialize, Deserialize)]
struct VaultData {
    version: u8,
    salt: Vec<u8>,
    nonce: Vec<u8>,
    ciphertext: Vec<u8>,
    checksum: Vec<u8>,
}

pub fn derive_key(password: &str, salt: &[u8]) -> Result<Vec<u8>, String> {
    let mut key = vec![0u8; 32];
    pbkdf2_hmac::<Sha256>(
        password.as_bytes(),
        salt,
        ITERATIONS,
        &mut key,
    );
    Ok(key)
}

fn generate_salt() -> Vec<u8> {
    use rand::RngCore;
    let mut salt = vec![0u8; SALT_SIZE];
    rand::thread_rng().fill_bytes(&mut salt);
    salt
}

fn calculate_checksum(data: &[u8]) -> Vec<u8> {
    use sha2::Digest;
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

pub fn derive_address_from_mnemonic(mnemonic: &str, _password: &str) -> Result<String, String> {
    let mnemonic_obj = Mnemonic::parse_in_normalized(Language::English, mnemonic)
        .map_err(|e| format!("Invalid mnemonic: {}", e))?;
    let seed = mnemonic_obj.to_seed("");

    // Simplified derivation - in production, use proper BIP-32 library
    // seed is already a [u8; 64] array

    // Use first 32 bytes as private key (simplified)
    let private_key_bytes = &seed[..32];

    // For now, return a placeholder address
    // In production, derive proper Ethereum address
    Ok(format!("0x{}", hex::encode(&private_key_bytes[0..20])))
}

pub fn encrypt_vault(mnemonic: &str, password: &str) -> Result<Vec<u8>, String> {
    let salt = generate_salt();
    let key = derive_key(password, &salt)?;
    let key = GenericArray::from_slice(&key);

    let cipher = Aes256Gcm::new(key);
    let nonce = Aes256Gcm::generate_nonce(&mut rand::thread_rng());

    let ciphertext = cipher.encrypt(&nonce, mnemonic.as_bytes().as_ref())
        .map_err(|e| format!("Encryption failed: {}", e))?;

    let checksum = calculate_checksum(mnemonic.as_bytes());

    let vault_data = VaultData {
        version: VAULT_VERSION,
        salt: salt.to_vec(),
        nonce: nonce.to_vec(),
        ciphertext,
        checksum,
    };

    serde_json::to_vec(&vault_data)
        .map_err(|e| format!("Failed to serialize vault: {}", e))
}

pub fn decrypt_vault(encrypted: &[u8], password: &str) -> Result<String, String> {
    let vault_data: VaultData = serde_json::from_slice(encrypted)
        .map_err(|e| format!("Failed to parse vault: {}", e))?;

    if vault_data.version != VAULT_VERSION {
        return Err(format!("Unsupported vault version: {}", vault_data.version));
    }

    let key = derive_key(password, &vault_data.salt)?;
    let key = GenericArray::from_slice(&key);

    let cipher = Aes256Gcm::new(key);
    let nonce = GenericArray::from_slice(&vault_data.nonce);

    let plaintext = cipher.decrypt(nonce, vault_data.ciphertext.as_ref())
        .map_err(|_| "Decryption failed: incorrect password or corrupted data".to_string())?;

    // Verify checksum
    let checksum = calculate_checksum(&plaintext);
    if checksum != vault_data.checksum {
        return Err("Data integrity check failed: vault may be corrupted".to_string());
    }

    String::from_utf8(plaintext).map_err(|e| format!("Invalid UTF-8: {}", e))
}

pub fn save_vault(usb_path: &str, mnemonic: &str, password: &str) -> Result<(), String> {
    let encrypted = encrypt_vault(mnemonic, password)?;
    let vault_path = Path::new(usb_path).join("wallet.vault");
    
    fs::write(&vault_path, encrypted).map_err(|e| format!("Failed to write vault: {}", e))?;
    
    Ok(())
}

pub fn load_vault(usb_path: &str, password: &str) -> Result<String, String> {
    let vault_path = Path::new(usb_path).join("wallet.vault");
    let encrypted = fs::read(&vault_path).map_err(|e| format!("Failed to read vault: {}", e))?;
    
    decrypt_vault(&encrypted, password)
}

pub fn create_unsigned_transaction(
    to: &str,
    amount: &str,
    gas_settings: &serde_json::Value,
    nonce: u64,
) -> Result<serde_json::Value, String> {
    Ok(serde_json::json!({
        "to": to,
        "value": amount,
        "nonce": nonce,
        "gasLimit": gas_settings.get("gasLimit").and_then(|v| v.as_u64()).unwrap_or(21000),
        "gasPrice": gas_settings.get("gasPrice").and_then(|v| v.as_f64()),
        "maxFeePerGas": gas_settings.get("maxFeePerGas").and_then(|v| v.as_f64()),
        "maxPriorityFeePerGas": gas_settings.get("maxPriorityFeePerGas").and_then(|v| v.as_f64()),
    }))
}

pub fn sign_transaction(tx: &serde_json::Value, _mnemonic: &str) -> Result<serde_json::Value, String> {
    // Parse transaction
    let to = tx.get("to").and_then(|v| v.as_str()).ok_or("Missing 'to'")?;
    let value = tx.get("value").and_then(|v| v.as_str()).ok_or("Missing 'value'")?;
    let nonce = tx.get("nonce").and_then(|v| v.as_u64()).ok_or("Missing 'nonce'")?;
    
    // In production, properly sign the transaction
    // For now, return placeholder
    Ok(serde_json::json!({
        "rawTx": format!("0x0000000000000000000000000000000000000000"),
        "hash": format!("0x0000000000000000000000000000000000000000"),
        "to": to,
        "value": value,
        "nonce": nonce,
    }))
}

pub fn generate_qr_code(uri: &str, path: &str) -> Result<String, String> {
    use qrcode_generator::QrCodeEcc;
    
    let png = qrcode_generator::to_png_to_vec(uri, QrCodeEcc::Medium, 250)
        .map_err(|e| format!("QR generation failed: {}", e))?;
    
    fs::write(path, png).map_err(|e| format!("Failed to write QR: {}", e))?;
    
    Ok(path.to_string())
}

pub fn decode_qr_from_image(_image_data: &[u8]) -> Result<String, String> {
    // This would use an image library + QR decoder
    // For now, return a placeholder
    Err("QR decoding not implemented".to_string())
}
