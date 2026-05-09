use aes_gcm::{Aes256Gcm, KeyInit, AeadCore};
use aes_gcm::aead::Aead;
use aes_gcm::aead::generic_array::GenericArray;
use pbkdf2::pbkdf2_hmac;
use sha2::{Sha256, Sha512, Digest};
use hmac::{Hmac, Mac};
use bip39::{Mnemonic, Language};
use k256::ecdsa::SigningKey;
use k256::SecretKey;
use hex;
use std::fs;
use std::path::Path;
use serde::{Deserialize, Serialize};

type HmacSha512 = Hmac<Sha512>;

const VAULT_VERSION: u8 = 2;
const ITERATIONS: u32 = 1_000_000;
const SALT_SIZE: usize = 32;

#[derive(Serialize, Deserialize)]
struct VaultData {
    version: u8,
    salt: Vec<u8>,
    nonce: Vec<u8>,
    ciphertext: Vec<u8>,
    // checksum removed: AES-GCM authentication tag is sufficient
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

/// BIP-32 child key derivation (hardened)
fn derive_child_key_hardened(parent_key: &[u8; 32], parent_chain: &[u8; 32], index: u32) -> ([u8; 32], [u8; 32]) {
    let mut mac = <HmacSha512 as Mac>::new_from_slice(parent_chain).expect("HMAC init failed");
    // Hardened: 0x00 || privkey || (index | 0x80000000)
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

/// BIP-32 child key derivation (non-hardened)
fn derive_child_key_normal(parent_key: &[u8; 32], parent_chain: &[u8; 32], index: u32) -> Result<([u8; 32], [u8; 32]), String> {
    assert!(index < 0x8000_0000, "Non-hardened index must be < 0x80000000");
    let mut mac = <HmacSha512 as Mac>::new_from_slice(parent_chain).expect("HMAC init failed");
    let compressed_pubkey = index_to_compressed_pubkey(parent_key)?;
    mac.update(&compressed_pubkey);
    mac.update(&index.to_be_bytes());
    let result = mac.finalize().into_bytes();

    use k256::elliptic_curve::ops::Reduce;
    use k256::Scalar;
    let mut il = [0u8; 32];
    let mut child_chain = [0u8; 32];
    il.copy_from_slice(&result[..32]);
    child_chain.copy_from_slice(&result[32..]);

    let scalar_il = Scalar::reduce_bytes((&il).into());
    let scalar_parent = Scalar::reduce_bytes(parent_key.into());
    let child_scalar = scalar_il + scalar_parent;
    let child_key: [u8; 32] = child_scalar.to_bytes().into();
    Ok((child_key, child_chain))
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

/// Derives Ethereum private key + address via BIP-44: m/44'/60'/0'/0/0
pub fn derive_eth_keypair(mnemonic: &str) -> Result<(Vec<u8>, String), String> {
    let mnemonic_obj = Mnemonic::parse_in_normalized(Language::English, mnemonic)
        .map_err(|e| format!("Invalid mnemonic: {}", e))?;
    let seed = mnemonic_obj.to_seed("");

    // Master key from seed
    let mut mac = <HmacSha512 as Mac>::new_from_slice(b"Bitcoin seed").expect("HMAC init");
    mac.update(&seed);
    let result = mac.finalize().into_bytes();
    let mut master_key = [0u8; 32];
    let mut master_chain = [0u8; 32];
    master_key.copy_from_slice(&result[..32]);
    master_chain.copy_from_slice(&result[32..]);

    // m/44'/60'/0' (hardened)
    let (k1, c1) = derive_child_key_hardened(&master_key, &master_chain, 44);
    let (k2, c2) = derive_child_key_hardened(&k1, &c1, 60);
    let (k3, c3) = derive_child_key_hardened(&k2, &c2, 0);

    // m/44'/60'/0'/0 (non-hardened change index)
    let (k4, c4) = derive_child_key_normal(&k3, &c3, 0)?;

    // m/44'/60'/0'/0/0 (non-hardened address index)
    let (final_key, _) = derive_child_key_normal(&k4, &c4, 0)?;

    let address = privkey_to_eth_address(&final_key)?;
    Ok((final_key.to_vec(), address))
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
    let encoded = pubkey.to_encoded_point(false);
    let pubkey_bytes = &encoded.as_bytes()[1..];
    let hash = keccak256(pubkey_bytes);
    let addr_bytes = &hash[12..];
    Ok(format!("0x{}", hex::encode(addr_bytes)))
}

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
    let vault_data = VaultData {
        version: VAULT_VERSION,
        salt: salt.to_vec(),
        nonce: nonce.to_vec(),
        ciphertext,
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

/// Parse ETH string to Wei (u128) without float precision loss
fn eth_str_to_wei(eth_str: &str) -> Result<u128, String> {
    let eth_str = eth_str.trim();
    let (int_part, frac_part) = if let Some(dot_pos) = eth_str.find('.') {
        (&eth_str[..dot_pos], &eth_str[dot_pos + 1..])
    } else {
        (eth_str, "")
    };

    let int_wei: u128 = int_part.parse::<u128>()
        .map_err(|_| format!("Invalid ETH integer part: {}", int_part))?
        .checked_mul(1_000_000_000_000_000_000u128)
        .ok_or("ETH value overflow")?;

    let frac_18 = format!("{:0<18}", frac_part);
    let frac_trimmed = &frac_18[..18];
    let frac_wei: u128 = frac_trimmed.parse::<u128>()
        .map_err(|_| format!("Invalid ETH fractional part: {}", frac_part))?;

    int_wei.checked_add(frac_wei).ok_or_else(|| "ETH value overflow".to_string())
}

/// Sign EIP-1559 transaction and return raw hex
pub fn sign_transaction(tx: &serde_json::Value, mnemonic: &str) -> Result<serde_json::Value, String> {
    use k256::ecdsa::signature::hazmat::PrehashSigner;

    let to = tx.get("to").and_then(|v| v.as_str()).ok_or("Missing 'to'")?;
    let value_str = tx.get("value").and_then(|v| v.as_str()).ok_or("Missing 'value'")?;
    let nonce = tx.get("nonce").and_then(|v| v.as_u64()).ok_or("Missing 'nonce'")?;
    let gas_limit = tx.get("gasLimit").and_then(|v| v.as_u64()).unwrap_or(21000);
    let max_fee = tx.get("maxFeePerGas").and_then(|v| v.as_f64()).unwrap_or(20.0);
    let max_priority = tx.get("maxPriorityFeePerGas").and_then(|v| v.as_f64()).unwrap_or(2.0);
    let chain_id: u64 = tx.get("chainId").and_then(|v| v.as_u64()).unwrap_or(1);

    let value_wei: u128 = eth_str_to_wei(value_str)?;
    let max_fee_wei: u128 = (max_fee * 1e9) as u128;
    let max_priority_wei: u128 = (max_priority * 1e9) as u128;

    let to_bytes = hex::decode(to.trim_start_matches("0x"))
        .map_err(|_| "Invalid 'to' address")?;

    let rlp_items: Vec<Vec<u8>> = vec![
        rlp_encode_u64(chain_id),
        rlp_encode_u64(nonce),
        rlp_encode_u128(max_priority_wei),
        rlp_encode_u128(max_fee_wei),
        rlp_encode_u64(gas_limit),
        rlp_encode_bytes(&to_bytes),
        rlp_encode_u128(value_wei),
        vec![0x80],
        vec![0xc0],
    ];

    let rlp_list = rlp_encode_list(&rlp_items);
    let mut signing_payload = vec![0x02u8];
    signing_payload.extend_from_slice(&rlp_list);

    let msg_hash = keccak256(&signing_payload);

    let (privkey_bytes, _) = derive_eth_keypair(mnemonic)?;
    let signing_key = SigningKey::from_bytes(privkey_bytes.as_slice().into())
        .map_err(|e| format!("Invalid private key: {}", e))?;

    let (sig, recovery_id) = signing_key.sign_prehash_recoverable(&msg_hash)
        .map_err(|e| format!("Signing failed: {}", e))?;
    let sig_bytes = sig.to_bytes();
    let r = &sig_bytes[..32];
    let s = &sig_bytes[32..];
    let v = recovery_id.to_byte() as u64;

    let signed_items: Vec<Vec<u8>> = vec![
        rlp_encode_u64(chain_id),
        rlp_encode_u64(nonce),
        rlp_encode_u128(max_priority_wei),
        rlp_encode_u128(max_fee_wei),
        rlp_encode_u64(gas_limit),
        rlp_encode_bytes(&to_bytes),
        rlp_encode_u128(value_wei),
        vec![0x80],
        vec![0xc0],
        rlp_encode_u64(v),
        rlp_encode_bytes(r),
        rlp_encode_bytes(s),
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

pub fn rlp_encode_bytes(data: &[u8]) -> Vec<u8> {
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
