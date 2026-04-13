use aes_gcm::{Aes256Gcm, KeyInit, AeadCore};
use aes_gcm::aead::Aead;
use aes_gcm::aead::generic_array::GenericArray;
use pbkdf2::pbkdf2_hmac;
use sha2::Sha256;
use bip39::{Mnemonic, Language};
use hex;
use std::fs;
use std::path::Path;

const SALT: &[u8] = b"zhorawallet_salt_v1";
const ITERATIONS: u32 = 600_000;

pub fn derive_key(password: &str) -> Result<Vec<u8>, String> {
    let mut key = vec![0u8; 32];
    pbkdf2_hmac::<Sha256>(
        password.as_bytes(),
        SALT,
        ITERATIONS,
        &mut key,
    );
    Ok(key)
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
    let key = derive_key(password)?;
    let key = GenericArray::from_slice(&key);
    
    let cipher = Aes256Gcm::new(key);
    let nonce = Aes256Gcm::generate_nonce(&mut rand::thread_rng());
    
    let ciphertext = cipher.encrypt(&nonce, mnemonic.as_bytes().as_ref())
        .map_err(|e| format!("Encryption failed: {}", e))?;
    
    let mut result = nonce.to_vec();
    result.extend_from_slice(&ciphertext);
    
    Ok(result)
}

pub fn decrypt_vault(encrypted: &[u8], password: &str) -> Result<String, String> {
    if encrypted.len() < 12 {
        return Err("Invalid encrypted data".to_string());
    }
    
    let key = derive_key(password)?;
    let key = GenericArray::from_slice(&key);
    
    let cipher = Aes256Gcm::new(key);
    let nonce = GenericArray::from_slice(&encrypted[..12]);
    let ciphertext = &encrypted[12..];
    
    let plaintext = cipher.decrypt(nonce, ciphertext)
        .map_err(|e| format!("Decryption failed: {}", e))?;
    
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
