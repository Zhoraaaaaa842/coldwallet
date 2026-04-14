use serde_json;
use std::fs;
use std::path::Path;

#[cfg(target_os = "windows")]
fn is_valid_usb_drive(drive_letter: char) -> bool {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    use winapi::um::fileapi::{GetDriveTypeW, GetDiskFreeSpaceExW};
    
    let drive_path = format!("{}:\\", drive_letter);
    let wide_path: Vec<u16> = OsStr::new(&drive_path)
        .encode_wide()
        .chain(Some(0))
        .collect();
    
    unsafe {
        let drive_type = GetDriveTypeW(wide_path.as_ptr());
        
        // DRIVE_REMOVABLE = 2 (USB, карты памяти)
        // DRIVE_FIXED = 3 (жесткие диски)
        // Мы принимаем только съёмные диски
        if drive_type != 2 {
            return false;
        }
        
        // Дополнительная проверка: пытаемся получить информацию о свободном месте
        // Это отсекает виртуальные/пустые съёмные диски
        let mut free_bytes_available: u64 = 0;
        let mut total_number_of_bytes: u64 = 0;
        let mut total_number_of_free_bytes: u64 = 0;
        
        let result = GetDiskFreeSpaceExW(
            wide_path.as_ptr(),
            &mut free_bytes_available as *mut _ as *mut _,
            &mut total_number_of_bytes as *mut _ as *mut _,
            &mut total_number_of_free_bytes as *mut _ as *mut _,
        );
        
        // Если не удалось получить информацию о диске - он невалидный
        if result == 0 {
            return false;
        }
        
        // Проверяем что диск имеет разумный размер (> 1 MB)
        // Это отсекает пустые/виртуальные диски
        total_number_of_bytes > 1_048_576
    }
}

pub struct UsbStatus {
    pub path: Option<String>,
    pub has_vault: bool,
    pub needs_format: bool,
}

pub fn check_usb_detailed() -> UsbStatus {
    if let Some(path) = detect_usb_drive() {
        let vault_path = Path::new(&path).join("wallet.vault");
        let has_vault = vault_path.exists();
        let needs_format = !has_vault;
        
        UsbStatus {
            path: Some(path),
            has_vault,
            needs_format,
        }
    } else {
        UsbStatus {
            path: None,
            has_vault: false,
            needs_format: false,
        }
    }
}

pub fn detect_usb_drive() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        // Check for removable drives only (D:, E:, F:, etc.)
        for drive in 'D'..='Z' {
            let path = format!("{}:\\", drive);
            if Path::new(&path).exists() && is_valid_usb_drive(drive) {
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
