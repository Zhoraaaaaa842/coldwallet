use serde_json;
use std::fs;
use std::path::Path;

pub fn detect_usb_drive() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::fs::MetadataExt;
        
        // Check for removable drives (D:, E:, F:, etc.)
        for drive in 'D'..='Z' {
            let path = format!("{}:\\", drive);
            if Path::new(&path).exists() {
                // Check if it's removable
                // In production, use Win32 API to check drive type
                return Some(path);
            }
        }
    }
    
    #[cfg(target_os = "linux")]
    {
        // Check /media/$USER for USB drives
        if let Ok(entries) = fs::read_dir("/media") {
            for entry in entries {
                if let Ok(entry) = entry {
                    if let Ok(entries) = fs::read_dir(entry.path()) {
                        for usb_entry in entries {
                            if let Ok(usb_entry) = usb_entry {
                                return Some(usb_entry.path().to_string_lossy().to_string());
                            }
                        }
                    }
                }
            }
        }
    }
    
    #[cfg(target_os = "macos")]
    {
        // Check /Volumes for USB drives
        if let Ok(entries) = fs::read_dir("/Volumes") {
            for entry in entries {
                if let Ok(entry) = entry {
                    let path = entry.path();
                    if path.exists() {
                        return Some(path.to_string_lossy().to_string());
                    }
                }
            }
        }
    }
    
    None
}

pub fn save_pending_transaction(usb_path: &str, tx: &serde_json::Value) -> Result<String, String> {
    let pending_dir = Path::new(usb_path).join("pending");
    fs::create_dir_all(&pending_dir).map_err(|e| format!("Failed to create pending dir: {}", e))?;
    
    let tx_id = format!("tx_{}.json", chrono::Utc::now().timestamp_millis());
    let tx_path = pending_dir.join(&tx_id);
    
    let json = serde_json::to_string_pretty(tx).map_err(|e| format!("Failed to serialize tx: {}", e))?;
    fs::write(&tx_path, json).map_err(|e| format!("Failed to write tx: {}", e))?;
    
    Ok(tx_path.to_string_lossy().to_string())
}

pub fn save_signed_transaction(usb_path: &str, tx: &serde_json::Value) -> Result<String, String> {
    let signed_dir = Path::new(usb_path).join("signed");
    fs::create_dir_all(&signed_dir).map_err(|e| format!("Failed to create signed dir: {}", e))?;
    
    let tx_id = format!("tx_{}.json", chrono::Utc::now().timestamp_millis());
    let tx_path = signed_dir.join(&tx_id);
    
    let json = serde_json::to_string_pretty(tx).map_err(|e| format!("Failed to serialize tx: {}", e))?;
    fs::write(&tx_path, json).map_err(|e| format!("Failed to write tx: {}", e))?;
    
    Ok(tx_path.to_string_lossy().to_string())
}

pub fn scan_pending_transactions(usb_path: &str) -> Result<Vec<serde_json::Value>, String> {
    let pending_dir = Path::new(usb_path).join("pending");
    
    if !pending_dir.exists() {
        return Ok(vec![]);
    }
    
    let mut transactions = vec![];
    let mut id_counter = 1;
    
    if let Ok(entries) = fs::read_dir(&pending_dir) {
        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("json") {
                    let content = fs::read_to_string(&path).map_err(|e| format!("Failed to read tx: {}", e))?;
                    let mut tx: serde_json::Value = serde_json::from_str(&content)
                        .map_err(|e| format!("Failed to parse tx: {}", e))?;
                    
                    tx["id"] = serde_json::json!(id_counter.to_string());
                    tx["path"] = serde_json::json!(path.to_string_lossy().to_string());
                    
                    transactions.push(tx);
                    id_counter += 1;
                }
            }
        }
    }
    
    Ok(transactions)
}

pub fn scan_signed_transactions(usb_path: &str) -> Result<Vec<serde_json::Value>, String> {
    let signed_dir = Path::new(usb_path).join("signed");
    
    if !signed_dir.exists() {
        return Ok(vec![]);
    }
    
    let mut transactions = vec![];
    let mut id_counter = 1;
    
    if let Ok(entries) = fs::read_dir(&signed_dir) {
        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                if path.extension().and_then(|e| e.to_str()) == Some("json") {
                    let content = fs::read_to_string(&path).map_err(|e| format!("Failed to read tx: {}", e))?;
                    let mut tx: serde_json::Value = serde_json::from_str(&content)
                        .map_err(|e| format!("Failed to parse tx: {}", e))?;
                    
                    tx["id"] = serde_json::json!(id_counter.to_string());
                    tx["path"] = serde_json::json!(path.to_string_lossy().to_string());
                    
                    transactions.push(tx);
                    id_counter += 1;
                }
            }
        }
    }
    
    Ok(transactions)
}

pub fn delete_pending_transaction(usb_path: &str, tx_id: &str) -> Result<(), String> {
    let pending_dir = Path::new(usb_path).join("pending");
    
    if let Ok(entries) = fs::read_dir(&pending_dir) {
        for entry in entries {
            if let Ok(entry) = entry {
                let path = entry.path();
                if path.file_stem().and_then(|e| e.to_str()) == Some(tx_id) {
                    fs::remove_file(&path).map_err(|e| format!("Failed to delete tx: {}", e))?;
                    return Ok(());
                }
            }
        }
    }
    
    Ok(())
}
