use aes_gcm::{Aes256Gcm, KeyInit, AeadCore};
use aes_gcm::aead::Aead;
use aes_gcm::aead::generic_array::GenericArray;
use pbkdf2::pbkdf2_hmac;
use sha2::{Sha256, Sha512, Digest};
use hmac::{Hmac, Mac};
use bip39::{Mnemonic, Language};
use k256::ecdsa::{SigningKey, signature::hazmat::PrehashSigner};
use k256::SecretKey;
use hex;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};

const VAULT_VERSION: u8 = 2;
const ITERATIONS: u32 = 1_000_000;
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
    pbkdf2_hmac::<Sha256>(password.as_bytes(), salt, ITERATIONS, &mut key);
    Ok(key)
}

fn generate_salt() -> Vec<u8> {
    use rand::RngCore;
    let mut salt = vec![0u8; SALT_SIZE];
    rand::thread_rng().fill_bytes(&mut salt);
    salt
}

fn calculate_checksum(data: &[u8]) -> Vec<u8> {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.finalize().to_vec()
}

/// BIP-32 child key derivation (hardened)
fn derive_child_key(parent_key: &[u8; 32], parent_chain: &[u8; 32], index: u32) -> ([u8; 32], [u8; 32]) {
    type HmacSha512 = Hmac<Sha512>;
    let mut mac = HmacSha512::new_from_slice(parent_chain).expect("HMAC init failed");
    mac.update(&[0u8]);
    mac.update(parent_key);
    mac.update(&(index | 0x8000_0000u32).to_be_bytes());
    let result = mac.finalize().into_bytes();
    let mut child_key = [0u8; 32];
    let mut child_chain = [0u8; 32];
    child_key.copy_from_slice(&result[..32]);
    child_chain.copy_from_slice(&result[32..]);
    (child_key, child_chain)
}

/// Keccak-256 hash
fn keccak256(data: &[u8]) -> [u8; 32] {
    use tiny_keccak::{Hasher, Keccak};
    let mut k = Keccak::v256();
    let mut out = [0u8; 32];
    k.update(data);
    k.finalize(&mut out);
    out
}

/// Derives real Ethereum private key + address via BIP-44: m/44'/60'/0'/0/0
pub fn derive_eth_keypair(mnemonic: &str) -> Result<(Vec<u8>, String), String> {
    let mnemonic_obj = Mnemonic::parse_in_normalized(Language::English, mnemonic)
        .map_err(|e| format!("Invalid mnemonic: {}", e))?;
    let seed = mnemonic_obj.to_seed("");

    // Master key from seed (HMAC-SHA512 with "Bitcoin seed")
    type HmacSha512 = Hmac<Sha512>;
    let mut mac = HmacSha512::new_from_slice(b"Bitcoin seed").expect("HMAC init");
    mac.update(&seed);
    let result = mac.finalize().into_bytes();
    let mut master_key = [0u8; 32];
    let mut master_chain = [0u8; 32];
    master_key.copy_from_slice(&result[..32]);
    master_chain.copy_from_slice(&result[32..]);

    // m/44'/60'/0'/0/0
    let (k1, c1) = derive_child_key(&master_key, &master_chain, 44);
    let (k2, c2) = derive_child_key(&k1, &c1, 60);
    let (k3, c3) = derive_child_key(&k2, &c2, 0);
    // Non-hardened for index 0 and account 0
    // m/44'/60'/0'/0 (non-hardened change)
    type HmacSha512b = Hmac<Sha512>;
    let mut mac2 = HmacSha512b::new_from_slice(&c3).expect("HMAC init");
    mac2.update(&[0u8]); // non-hardened: pubkey prefix + index
    mac2.update(&index_to_compressed_pubkey(&k3)?);
    mac2.update(&0u32.to_be_bytes());
    let r2 = mac2.finalize().into_bytes();
    let mut change_key = [0u8; 32];
    let mut change_chain = [0u8; 32];
    change_key.copy_from_slice(&r2[..32]);
    change_chain.copy_from_slice(&r2[32..]);

    // Final index 0 (non-hardened)
    let mut mac3 = HmacSha512b::new_from_slice(&change_chain).expect("HMAC init");
    mac3.update(&[0u8]);
    mac3.update(&index_to_compressed_pubkey(&change_key)?);
    mac3.update(&0u32.to_be_bytes());
    let r3 = mac3.finalize().into_bytes();
    let mut final_key = [0u8; 32];
    final_key.copy_from_slice(&r3[..32]);

    // Add keys mod n (secp256k1 addition)
    use k256::elliptic_curve::ops::Reduce;
    use k256::{U256, Scalar};
    let scalar_parent = Scalar::reduce_bytes((&change_key).into());
    let scalar_child = Scalar::reduce_bytes((&final_key).into());
    let scalar_sum = scalar_parent + scalar_child;
    let child_key_bytes: [u8; 32] = scalar_sum.to_bytes().into();

    let address = privkey_to_eth_address(&child_key_bytes)?;
    Ok((child_key_bytes.to_vec(), address))
}

fn index_to_compressed_pubkey(privkey: &[u8; 32]) -> Result<Vec<u8>, String> {
    use k256::elliptic_curve::sec1::ToEncodedPoint;
    let secret = SecretKey::from_bytes(privkey.into())
        .map_err(|e| format!("Invalid private key: {}", e))?;
    let pubkey = secret.public_key();
    Ok(pubkey.to_encoded_point(true).as_bytes().to_vec())
}

fn privkey_to_eth_address(privkey: &[u8; 32]) -> Result<String, String> {
    use k256::elliptic_curve::sec1::ToEncodedPoint;
    let secret = SecretKey::from_bytes(privkey.into())
        .map_err(|e| format!("Invalid private key: {}", e))?;
    let pubkey = secret.public_key();
    // Uncompressed pubkey, skip 0x04 prefix → 64 bytes
    let encoded = pubkey.to_encoded_point(false);
    let pubkey_bytes = &encoded.as_bytes()[1..];
    let hash = keccak256(pubkey_bytes);
    // Last 20 bytes = Ethereum address
    let addr_bytes = &hash[12..];
    Ok(format!("0x{}", hex::encode(addr_bytes)))
}

/// Public wrapper used by commands.rs
pub fn derive_address_from_mnemonic(mnemonic: &str, _password: &str) -> Result<String, String> {
    let (_, address) = derive_eth_keypair(mnemonic)?;
    Ok(address)
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
    serde_json::to_vec(&vault_data).map_err(|e| format!("Failed to serialize vault: {}", e))
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

/// Sign EIP-1559 transaction and return raw hex
pub fn sign_transaction(tx: &serde_json::Value, mnemonic: &str) -> Result<serde_json::Value, String> {
    let to = tx.get("to").and_then(|v| v.as_str()).ok_or("Missing 'to'")?;
    let value_str = tx.get("value").and_then(|v| v.as_str()).ok_or("Missing 'value'")?;
    let nonce = tx.get("nonce").and_then(|v| v.as_u64()).ok_or("Missing 'nonce'")?;
    let gas_limit = tx.get("gasLimit").and_then(|v| v.as_u64()).unwrap_or(21000);
    let max_fee = tx.get("maxFeePerGas").and_then(|v| v.as_f64()).unwrap_or(20.0);
    let max_priority = tx.get("maxPriorityFeePerGas").and_then(|v| v.as_f64()).unwrap_or(2.0);
    let chain_id: u64 = tx.get("chainId").and_then(|v| v.as_u64()).unwrap_or(1);

    // Parse value: accept ETH float string → wei u128
    let value_eth: f64 = value_str.parse().map_err(|_| "Invalid value format")?;
    let value_wei: u128 = (value_eth * 1e18) as u128;

    // Convert gwei → wei
    let max_fee_wei: u128 = (max_fee * 1e9) as u128;
    let max_priority_wei: u128 = (max_priority * 1e9) as u128;

    // Parse to address
    let to_bytes = hex::decode(to.trim_start_matches("0x"))
        .map_err(|_| "Invalid 'to' address")?;

    // EIP-1559 RLP encoding: [chain_id, nonce, max_priority, max_fee, gas_limit, to, value, data, access_list]
    let mut rlp_items: Vec<Vec<u8>> = vec![
        rlp_encode_u64(chain_id),
        rlp_encode_u64(nonce),
        rlp_encode_u128(max_priority_wei),
        rlp_encode_u128(max_fee_wei),
        rlp_encode_u64(gas_limit),
        to_bytes.clone(),
        rlp_encode_u128(value_wei),
        vec![],    // data (empty)
        vec![0xc0], // access_list (empty list)
    ];

    let rlp_list = rlp_encode_list(&rlp_items);
    // EIP-2718 type 2 prefix
    let mut signing_payload = vec![0x02u8];
    signing_payload.extend_from_slice(&rlp_list);

    // Hash the signing payload
    let msg_hash = keccak256(&signing_payload);

    // Get private key
    let (privkey_bytes, _) = derive_eth_keypair(mnemonic)?;
    let signing_key = SigningKey::from_bytes(privkey_bytes.as_slice().into())
        .map_err(|e| format!("Invalid private key: {}", e))?;

    // Sign
    let (sig, recovery_id) = signing_key.sign_prehash_recoverable(&msg_hash)
        .map_err(|e| format!("Signing failed: {}", e))?;
    let sig_bytes = sig.to_bytes();
    let r = &sig_bytes[..32];
    let s = &sig_bytes[32..];
    let v = recovery_id.to_byte() as u64;

    // Encode signed tx RLP
    let signed_items: Vec<Vec<u8>> = vec![
        rlp_encode_u64(chain_id),
        rlp_encode_u64(nonce),
        rlp_encode_u128(max_priority_wei),
        rlp_encode_u128(max_fee_wei),
        rlp_encode_u64(gas_limit),
        to_bytes,
        rlp_encode_u128(value_wei),
        vec![],
        vec![0xc0],
        rlp_encode_u64(v),
        r.to_vec(),
        s.to_vec(),
    ];
    let signed_rlp = rlp_encode_list(&signed_items);
    let mut raw_tx = vec![0x02u8];
    raw_tx.extend_from_slice(&signed_rlp);

    let raw_hex = format!("0x{}", hex::encode(&raw_tx));
    let tx_hash = format!("0x{}", hex::encode(keccak256(&raw_tx)));

    Ok(serde_json::json!({
        "raw": raw_hex,
        "hash": tx_hash,
        "to": to,
        "value": value_str,
        "nonce": nonce,
    }))
}

// --- Minimal RLP helpers ---

fn rlp_encode_u64(v: u64) -> Vec<u8> {
    if v == 0 { return vec![0x80]; }
    let bytes = v.to_be_bytes();
    let trimmed: Vec<u8> = bytes.iter().skip_while(|&&b| b == 0).cloned().collect();
    rlp_encode_bytes(&trimmed)
}

fn rlp_encode_u128(v: u128) -> Vec<u8> {
    if v == 0 { return vec![0x80]; }
    let bytes = v.to_be_bytes();
    let trimmed: Vec<u8> = bytes.iter().skip_while(|&&b| b == 0).cloned().collect();
    rlp_encode_bytes(&trimmed)
}

fn rlp_encode_bytes(data: &[u8]) -> Vec<u8> {
    if data.len() == 1 && data[0] < 0x80 {
        return data.to_vec();
    }
    let mut out = rlp_length_prefix(data.len(), 0x80);
    out.extend_from_slice(data);
    out
}

fn rlp_encode_list(items: &[Vec<u8>]) -> Vec<u8> {
    let payload: Vec<u8> = items.iter().flat_map(|i| i.clone()).collect();
    let mut out = rlp_length_prefix(payload.len(), 0xc0);
    out.extend_from_slice(&payload);
    out
}

fn rlp_length_prefix(length: usize, offset: u8) -> Vec<u8> {
    if length < 56 {
        vec![offset + length as u8]
    } else {
        let len_bytes = length.to_be_bytes();
        let trimmed: Vec<u8> = len_bytes.iter().skip_while(|&&b| b == 0).cloned().collect();
        let mut out = vec![offset + 55 + trimmed.len() as u8];
        out.extend_from_slice(&trimmed);
        out
    }
}

pub fn generate_qr_code(uri: &str, path: &str) -> Result<String, String> {
    use qrcode_generator::QrCodeEcc;
    let png = qrcode_generator::to_png_to_vec(uri, QrCodeEcc::Medium, 250)
        .map_err(|e| format!("QR generation failed: {}", e))?;
    fs::write(path, png).map_err(|e| format!("Failed to write QR: {}", e))?;
    Ok(path.to_string())
}

pub fn decode_qr_from_image(_image_data: &[u8]) -> Result<String, String> {
    Err("QR decoding requires a native library; scan QR manually or use camera input".to_string())
}
