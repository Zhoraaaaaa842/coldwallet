use tauri::State;
use crate::state::AppState;
use crate::usb;
use bip39::{Mnemonic, Language};

#[tauri::command]
pub fn check_usb_status(state: State<AppState>) -> Result<String, String> {
    match usb::detect_usb_drive() {
        Some(path) => {
            let mut usb_path = state.usb_path.lock().map_err(|e| e.to_string())?;
            *usb_path = Some(path.clone());
            Ok("connected".to_string())
        }
        None => Ok("disconnected".to_string()),
    }
}

#[tauri::command]
pub fn initialize_wallet(password: String, state: State<AppState>) -> Result<String, String> {
    let mut wallet = state.wallet.lock().map_err(|e| e.to_string())?;
    
    // Generate mnemonic (24 words = 256 bits of entropy)
    let mut entropy = [0u8; 32];
    use rand::RngCore;
    rand::thread_rng().fill_bytes(&mut entropy);
    let mnemonic = Mnemonic::from_entropy_in(Language::English, &entropy)
        .map_err(|e| format!("Failed to generate mnemonic: {}", e))?;
    let mnemonic_phrase = mnemonic.to_string();
    
    // Derive key and address from mnemonic
    let address = crate::crypto::derive_address_from_mnemonic(&mnemonic_phrase, &password)?;
    
    wallet.address = Some(address.clone());
    wallet.mnemonic = Some(mnemonic_phrase);
    wallet.is_initialized = true;
    wallet.is_locked = false;
    
    // Save encrypted vault to USB
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        crate::crypto::save_vault(&usb_path, &wallet.mnemonic.as_ref().unwrap(), &password)?;
    }
    
    Ok(address)
}

#[tauri::command]
pub fn import_from_mnemonic(mnemonic: String, password: String, state: State<AppState>) -> Result<String, String> {
    let mut wallet = state.wallet.lock().map_err(|e| e.to_string())?;
    
    // Validate mnemonic
    let _ = Mnemonic::parse_in_normalized(Language::English, &mnemonic)
        .map_err(|_| "Invalid mnemonic phrase")?;
    
    // Derive address
    let address = crate::crypto::derive_address_from_mnemonic(&mnemonic, &password)?;
    
    wallet.address = Some(address.clone());
    wallet.mnemonic = Some(mnemonic);
    wallet.is_initialized = true;
    wallet.is_locked = false;
    
    // Save encrypted vault to USB
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        crate::crypto::save_vault(&usb_path, &wallet.mnemonic.as_ref().unwrap(), &password)?;
    }
    
    Ok(address)
}

#[tauri::command]
pub fn unlock_wallet(password: String, state: State<AppState>) -> Result<String, String> {
    let mut wallet = state.wallet.lock().map_err(|e| e.to_string())?;
    
    // Load vault from USB
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        let mnemonic = crate::crypto::load_vault(&usb_path, &password)?;
        let address = crate::crypto::derive_address_from_mnemonic(&mnemonic, &password)?;
        
        wallet.address = Some(address.clone());
        wallet.mnemonic = Some(mnemonic);
        wallet.is_locked = false;
        
        Ok(address)
    } else {
        Err("USB drive not found".to_string())
    }
}

#[tauri::command]
pub async fn get_balance(address: String, state: State<'_, AppState>) -> Result<String, String> {
    let rpc_url = state.rpc_url.lock().map_err(|e| e.to_string())?.clone();
    crate::network::get_balance(&rpc_url, &address).await
}

#[tauri::command]
pub async fn get_nonce(address: String, state: State<'_, AppState>) -> Result<u64, String> {
    let rpc_url = state.rpc_url.lock().map_err(|e| e.to_string())?.clone();
    crate::network::get_nonce(&rpc_url, &address).await
}

#[tauri::command]
pub async fn fetch_eth_price_rub(state: State<'_, AppState>) -> Result<f64, String> {
    let price = crate::network::fetch_eth_price_rub().await?;
    let mut price_cache = state.price_cache.lock().map_err(|e| e.to_string())?;
    *price_cache = price;
    Ok(price)
}

#[tauri::command]
pub async fn get_transaction_history(address: String, state: State<'_, AppState>) -> Result<Vec<serde_json::Value>, String> {
    let rpc_url = state.rpc_url.lock().map_err(|e| e.to_string())?.clone();
    crate::network::get_transaction_history(&rpc_url, &address).await
}

#[tauri::command]
pub async fn fetch_gas_settings(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let rpc_url = state.rpc_url.lock().map_err(|e| e.to_string())?.clone();
    crate::network::fetch_gas_settings(&rpc_url).await
}

#[tauri::command]
pub fn create_unsigned_transaction(
    to: String,
    amount: String,
    gas_settings: serde_json::Value,
    nonce: u64,
    state: State<AppState>,
) -> Result<String, String> {
    let wallet = state.wallet.lock().map_err(|e| e.to_string())?;
    
    if wallet.is_locked || wallet.address.is_none() {
        return Err("Wallet is locked".to_string());
    }
    
    // Create unsigned transaction
    let tx = crate::crypto::create_unsigned_transaction(&to, &amount, &gas_settings, nonce)?;
    
    // Save to USB pending folder
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        let tx_path = crate::usb::save_pending_transaction(&usb_path, &tx)?;
        Ok(tx_path)
    } else {
        Err("USB drive not found".to_string())
    }
}

#[tauri::command]
pub fn scan_pending_transactions(state: State<AppState>) -> Result<Vec<serde_json::Value>, String> {
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        crate::usb::scan_pending_transactions(&usb_path)
    } else {
        Err("USB drive not found".to_string())
    }
}

#[tauri::command]
pub fn scan_signed_transactions(state: State<AppState>) -> Result<Vec<serde_json::Value>, String> {
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        crate::usb::scan_signed_transactions(&usb_path)
    } else {
        Err("USB drive not found".to_string())
    }
}

#[tauri::command]
pub fn sign_transaction(tx: serde_json::Value, state: State<AppState>) -> Result<String, String> {
    let wallet = state.wallet.lock().map_err(|e| e.to_string())?;
    
    if wallet.is_locked || wallet.mnemonic.is_none() {
        return Err("Wallet is locked".to_string());
    }
    
    let mnemonic = wallet.mnemonic.as_ref().unwrap();
    let signed_tx = crate::crypto::sign_transaction(&tx, mnemonic)?;
    
    // Save to USB signed folder
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        let tx_path = crate::usb::save_signed_transaction(&usb_path, &signed_tx)?;
        
        // Delete from pending
        if let Some(tx_id) = tx.get("id").and_then(|v| v.as_str()) {
            crate::usb::delete_pending_transaction(&usb_path, tx_id)?;
        }
        
        Ok(tx_path)
    } else {
        Err("USB drive not found".to_string())
    }
}

#[tauri::command]
pub async fn broadcast_transaction(raw_tx: String, state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let rpc_url = state.rpc_url.lock().map_err(|e| e.to_string())?.clone();
    let receipt = crate::network::broadcast_transaction(&rpc_url, &raw_tx).await?;
    
    // Delete from signed folder
    // (implementation omitted for brevity)
    
    Ok(receipt)
}

#[tauri::command]
pub fn save_qr_image(uri: String, path: String) -> Result<String, String> {
    crate::crypto::generate_qr_code(&uri, &path)
}

#[tauri::command]
pub fn decode_qr_from_image(image_data: Vec<u8>) -> Result<String, String> {
    crate::crypto::decode_qr_from_image(&image_data)
}

#[tauri::command]
pub fn get_mnemonic(state: State<AppState>) -> Result<String, String> {
    let wallet = state.wallet.lock().map_err(|e| e.to_string())?;
    
    if wallet.is_locked || wallet.mnemonic.is_none() {
        return Err("Wallet is locked".to_string());
    }
    
    Ok(wallet.mnemonic.clone().unwrap_or_default())
}
