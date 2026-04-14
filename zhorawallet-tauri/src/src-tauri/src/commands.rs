use tauri::State;
use crate::state::AppState;
use crate::usb;
use crate::networks::Network;
use crate::address_book::{AddressBook, Contact};
use crate::transaction_cache::{Transaction, TransactionCache};
use crate::validation;
use bip39::{Mnemonic, Language};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct UsbStatusResponse {
    pub status: String,
    pub path: Option<String>,
    pub has_vault: bool,
    pub needs_format: bool,
}

#[tauri::command]
pub fn check_usb_status(state: State<AppState>) -> Result<UsbStatusResponse, String> {
    let detailed = usb::check_usb_detailed();
    
    match detailed.path {
        Some(path) => {
            let mut usb_path = state.usb_path.lock().map_err(|e| e.to_string())?;
            *usb_path = Some(path.clone());
            Ok(UsbStatusResponse {
                status: "connected".to_string(),
                path: Some(path),
                has_vault: detailed.has_vault,
                needs_format: detailed.needs_format,
            })
        }
        None => Ok(UsbStatusResponse {
            status: "disconnected".to_string(),
            path: None,
            has_vault: false,
            needs_format: false,
        }),
    }
}

#[tauri::command]
pub fn initialize_wallet(password: String, state: State<AppState>) -> Result<String, String> {
    // Validate password strength
    validation::validate_password_strength(&password)?;

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
    // Validate mnemonic and password
    validation::validate_mnemonic(&mnemonic)?;
    validation::validate_password_strength(&password)?;

    let mut wallet = state.wallet.lock().map_err(|e| e.to_string())?;

    // Validate mnemonic with BIP39
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
    let rpc_url = state.current_network.lock().map_err(|e| e.to_string())?.rpc_url.clone();
    crate::network::get_balance(&rpc_url, &address).await
}

#[tauri::command]
pub async fn get_nonce(address: String, state: State<'_, AppState>) -> Result<u64, String> {
    let rpc_url = state.current_network.lock().map_err(|e| e.to_string())?.rpc_url.clone();
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
    let rpc_url = state.current_network.lock().map_err(|e| e.to_string())?.rpc_url.clone();
    crate::network::get_transaction_history(&rpc_url, &address).await
}

#[tauri::command]
pub async fn fetch_gas_settings(state: State<'_, AppState>) -> Result<serde_json::Value, String> {
    let rpc_url = state.current_network.lock().map_err(|e| e.to_string())?.rpc_url.clone();
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
    let rpc_url = state.current_network.lock().map_err(|e| e.to_string())?.rpc_url.clone();
    let receipt = crate::network::broadcast_transaction(&rpc_url, &raw_tx).await?;

    // Delete the corresponding signed transaction file from USB
    if let Some(usb_path) = state.usb_path.lock().ok().and_then(|p| p.clone()) {
        let signed_dir = std::path::Path::new(&usb_path).join("signed");
        if signed_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(&signed_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().and_then(|e| e.to_str()) == Some("json") {
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            if let Ok(tx_json) = serde_json::from_str::<serde_json::Value>(&content) {
                                // Match by raw_tx field or by hash
                                let matches = tx_json.get("raw")
                                    .and_then(|v| v.as_str())
                                    .map(|r| r == raw_tx)
                                    .unwrap_or(false);
                                if matches {
                                    let _ = std::fs::remove_file(&path);
                                    break;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

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

#[tauri::command]
pub fn get_all_networks() -> Result<Vec<Network>, String> {
    Ok(Network::get_all_networks())
}

#[tauri::command]
pub fn get_current_network(state: State<AppState>) -> Result<Network, String> {
    let network = state.current_network.lock().map_err(|e| e.to_string())?;
    Ok(network.clone())
}

#[tauri::command]
pub fn switch_network(network_id: String, state: State<AppState>) -> Result<Network, String> {
    let network = Network::get_by_id(&network_id)
        .ok_or_else(|| format!("Network not found: {}", network_id))?;

    let mut current_network = state.current_network.lock().map_err(|e| e.to_string())?;
    *current_network = network.clone();

    Ok(network)
}

// Address Book Commands

#[tauri::command]
pub fn add_contact(
    name: String,
    address: String,
    note: Option<String>,
    state: State<AppState>,
) -> Result<Contact, String> {
    // Validate inputs
    let sanitized_name = validation::sanitize_contact_name(&name)?;
    let validated_address = validation::validate_ethereum_address(&address)?;

    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let book_path = format!("{}/address_book.json", usb_path);
    let mut book = AddressBook::load_from_file(&book_path)?;

    let contact = Contact {
        id: uuid::Uuid::new_v4().to_string(),
        name: sanitized_name,
        address: validated_address,
        note,
        created_at: chrono::Utc::now().timestamp(),
        updated_at: chrono::Utc::now().timestamp(),
    };

    book.add_contact(contact.clone())?;
    book.save_to_file(&book_path)?;

    Ok(contact)
}

#[tauri::command]
pub fn update_contact(
    id: String,
    name: String,
    address: String,
    note: Option<String>,
    state: State<AppState>,
) -> Result<(), String> {
    // Validate inputs
    let sanitized_name = validation::sanitize_contact_name(&name)?;
    let validated_address = validation::validate_ethereum_address(&address)?;

    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let book_path = format!("{}/address_book.json", usb_path);
    let mut book = AddressBook::load_from_file(&book_path)?;

    book.update_contact(&id, sanitized_name, validated_address, note)?;
    book.save_to_file(&book_path)?;

    Ok(())
}

#[tauri::command]
pub fn delete_contact(id: String, state: State<AppState>) -> Result<(), String> {
    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let book_path = format!("{}/address_book.json", usb_path);
    let mut book = AddressBook::load_from_file(&book_path)?;

    book.delete_contact(&id)?;
    book.save_to_file(&book_path)?;

    Ok(())
}

#[tauri::command]
pub fn get_all_contacts(state: State<AppState>) -> Result<Vec<Contact>, String> {
    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let book_path = format!("{}/address_book.json", usb_path);
    let book = AddressBook::load_from_file(&book_path)?;

    Ok(book.get_all_contacts())
}

#[tauri::command]
pub fn search_contacts(query: String, state: State<AppState>) -> Result<Vec<Contact>, String> {
    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let book_path = format!("{}/address_book.json", usb_path);
    let book = AddressBook::load_from_file(&book_path)?;

    Ok(book.search_contacts(&query))
}

// Transaction Cache Commands

#[tauri::command]
pub async fn get_cached_transactions(
    address: String,
    force_refresh: bool,
    state: State<'_, AppState>,
) -> Result<Vec<Transaction>, String> {
    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let network = state.current_network.lock().map_err(|e| e.to_string())?.clone();
    let cache_path = format!("{}/tx_cache.json", usb_path);

    let mut cache_map = TransactionCache::load_from_file(&cache_path)?;
    let cache_key = TransactionCache::get_cache_key(&address, &network.id);

    let should_refresh = force_refresh ||
        cache_map.get(&cache_key)
            .map(|c| c.is_stale(300)) // 5 minutes
            .unwrap_or(true);

    if should_refresh {
        // Fetch fresh data
        let tx_history = crate::network::get_transaction_history(&network.rpc_url, &address).await?;

        let transactions: Vec<Transaction> = tx_history.iter().map(|tx| {
            let from = tx.get("from").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let to = tx.get("to").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let value = tx.get("value").and_then(|v| v.as_str()).unwrap_or("0").to_string();
            let value_eth = value.parse::<f64>().unwrap_or(0.0) / 1e18;

            Transaction {
                hash: tx.get("hash").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                from: from.clone(),
                to: to.clone(),
                value,
                value_eth,
                gas_used: tx.get("gasUsed").and_then(|v| v.as_str()).unwrap_or("0").to_string(),
                gas_price: tx.get("gasPrice").and_then(|v| v.as_str()).unwrap_or("0").to_string(),
                timestamp: tx.get("timestamp").and_then(|v| v.as_str()).and_then(|s| s.parse().ok()).unwrap_or(0),
                block_number: tx.get("blockNumber").and_then(|v| v.as_str()).and_then(|s| s.parse().ok()).unwrap_or(0),
                status: tx.get("status").and_then(|v| v.as_str()).unwrap_or("1").to_string(),
                tx_type: if from.to_lowercase() == address.to_lowercase() { "outgoing" } else { "incoming" }.to_string(),
                network_id: network.id.clone(),
            }
        }).collect();

        let mut tx_cache = cache_map.entry(cache_key.clone())
            .or_insert_with(|| TransactionCache::new(address.clone(), network.id.clone()));

        tx_cache.update_transactions(transactions);
        TransactionCache::save_to_file(&cache_map, &cache_path)?;
    }

    let cache = cache_map.get(&cache_key)
        .ok_or("Cache not found")?;

    Ok(cache.get_filtered_transactions(None, None))
}

#[tauri::command]
pub fn get_balance_summary(
    address: String,
    state: State<AppState>,
) -> Result<serde_json::Value, String> {
    let usb_path = state.usb_path.lock().map_err(|e| e.to_string())?
        .clone()
        .ok_or("USB drive not found")?;

    let network = state.current_network.lock().map_err(|e| e.to_string())?.clone();
    let cache_path = format!("{}/tx_cache.json", usb_path);

    let cache_map = TransactionCache::load_from_file(&cache_path)?;
    let cache_key = TransactionCache::get_cache_key(&address, &network.id);

    if let Some(cache) = cache_map.get(&cache_key) {
        let (total_in, total_out) = cache.get_balance_changes();

        Ok(serde_json::json!({
            "totalReceived": total_in,
            "totalSent": total_out,
            "transactionCount": cache.transactions.len(),
            "lastUpdated": cache.last_updated,
        }))
    } else {
        Ok(serde_json::json!({
            "totalReceived": 0.0,
            "totalSent": 0.0,
            "transactionCount": 0,
            "lastUpdated": 0,
        }))
    }
}
