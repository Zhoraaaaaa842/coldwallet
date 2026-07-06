use serde_json;
use std::fs;
use std::path::Path;

#[cfg(target_os = "windows")]
fn is_valid_usb_drive(drive_letter: char) -> bool {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    use winapi::um::fileapi::{GetDriveTypeW, GetDiskFreeSpaceExW, CreateFileW, OPEN_EXISTING};
    use winapi::um::winnt::{GENERIC_READ, FILE_SHARE_READ, FILE_SHARE_WRITE};
    use winapi::um::handleapi::{CloseHandle, INVALID_HANDLE_VALUE};
    use winapi::um::ioapiset::DeviceIoControl;
    use winapi::um::winioctl::{IOCTL_STORAGE_QUERY_PROPERTY, StorageDeviceProperty, StorageAdapterProperty};
    use winapi::shared::minwindef::DWORD;

    let drive_path = format!("{}:\\\\", drive_letter);
    let wide_path: Vec<u16> = OsStr::new(&drive_path)
        .encode_wide()
        .chain(Some(0))
        .collect();

    unsafe {
        let drive_type = GetDriveTypeW(wide_path.as_ptr());
        if drive_type != 2 {
            return false;
        }

        let mut free_bytes: u64 = 0;
        let mut total_bytes: u64 = 0;
        let mut total_free: u64 = 0;
        let ok = GetDiskFreeSpaceExW(
            wide_path.as_ptr(),
            &mut free_bytes as *mut _ as *mut _,
            &mut total_bytes as *mut _ as *mut _,
            &mut total_free as *mut _ as *mut _,
        );
        if ok == 0 || total_bytes < 1_048_576 {
            return false;
        }
        if total_bytes > 274_877_906_944u64 {
            return false;
        }

        let device_path = format!("\\\\\\.\\\\{}:", drive_letter);
        let wide_device: Vec<u16> = OsStr::new(&device_path)
            .encode_wide()
            .chain(Some(0))
            .collect();

        let handle = CreateFileW(
            wide_device.as_ptr(),
            0,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            std::ptr::null_mut(),
            OPEN_EXISTING,
            0,
            std::ptr::null_mut(),
        );

        if handle == INVALID_HANDLE_VALUE {
            return true;
        }

        #[repr(C)]
        struct StoragePropertyQuery {
            property_id: u32,
            query_type: u32,
            additional_parameters: [u8; 1],
        }

        #[repr(C)]
        struct StorageDeviceDescriptor {
            version: u32,
            size: u32,
            device_type: u8,
            device_type_modifier: u8,
            removable_media: u8,
            command_queueing: u8,
            vendor_id_offset: u32,
            product_id_offset: u32,
            product_revision_offset: u32,
            serial_number_offset: u32,
            bus_type: u32,
            raw_properties_length: u32,
            raw_device_properties: [u8; 1],
        }

        let query = StoragePropertyQuery {
            property_id: 0,
            query_type: 0,
            additional_parameters: [0],
        };

        let mut descriptor = std::mem::zeroed::<StorageDeviceDescriptor>();
        let mut bytes_returned: DWORD = 0;

        let result = DeviceIoControl(
            handle,
            IOCTL_STORAGE_QUERY_PROPERTY,
            &query as *const _ as *mut _,
            std::mem::size_of::<StoragePropertyQuery>() as DWORD,
            &mut descriptor as *mut _ as *mut _,
            std::mem::size_of::<StorageDeviceDescriptor>() as DWORD,
            &mut bytes_returned,
            std::ptr::null_mut(),
        );

        CloseHandle(handle);

        if result == 0 {
            return true;
        }

        descriptor.bus_type == 7
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
        UsbStatus { path: Some(path), has_vault, needs_format }
    } else {
        UsbStatus { path: None, has_vault: false, needs_format: false }
    }
}

pub fn detect_usb_drive() -> Option<String> {
    #[cfg(target_os = "windows")]
    {
        for drive in 'D'..='Z' {
            let path = format!("{}:\\\\", drive);
            if Path::new(&path).exists() && is_valid_usb_drive(drive) {
                return Some(path);
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
        if let Ok(user_entries) = fs::read_dir("/media") {
            for user_entry in user_entries.flatten() {
                let user_path = user_entry.path();
                if !user_path.is_dir() { continue; }
                if let Ok(device_entries) = fs::read_dir(&user_path) {
                    for device_entry in device_entries.flatten() {
                        let mount_point = device_entry.path();
                        if mount_point.is_dir() {
                            return Some(mount_point.to_string_lossy().to_string());
                        }
                    }
                }
            }
        }
    }

    #[cfg(target_os = "macos")]
    {
        const SYSTEM_VOLUMES: &[&str] = &["Macintosh HD", "Macintosh SSD", "System"];
        if let Ok(entries) = fs::read_dir("/Volumes") {
            for entry in entries.flatten() {
                let path = entry.path();
                if !path.is_dir() { continue; }
                let name = entry.file_name();
                let name_str = name.to_string_lossy();
                if SYSTEM_VOLUMES.iter().any(|s| name_str.eq_ignore_ascii_case(s)) { continue; }
                if name_str.starts_with('.') { continue; }
                return Some(path.to_string_lossy().to_string());
            }
        }
    }

    None
}

/// FIX #2: Atomic write for pending transactions.
pub fn save_pending_transaction(usb_path: &str, tx: &serde_json::Value) -> Result<String, String> {
    let pending_dir = Path::new(usb_path).join("pending");
    fs::create_dir_all(&pending_dir).map_err(|e| format!("Failed to create pending dir: {}", e))?;
    let tx_id = format!("tx_{}.json", chrono::Utc::now().timestamp_millis());
    let tx_path = pending_dir.join(&tx_id);
    let tmp_path = pending_dir.join(format!("{}.tmp", tx_id));
    let json = serde_json::to_string_pretty(tx).map_err(|e| format!("Failed to serialize tx: {}", e))?;
    fs::write(&tmp_path, &json).map_err(|e| format!("Failed to write tx tmp: {}", e))?;
    fs::rename(&tmp_path, &tx_path).map_err(|e| format!("Failed to rename tx: {}", e))?;
    Ok(tx_path.to_string_lossy().to_string())
}

/// FIX #2: Atomic write for signed transactions.
pub fn save_signed_transaction(usb_path: &str, tx: &serde_json::Value) -> Result<String, String> {
    let signed_dir = Path::new(usb_path).join("signed");
    fs::create_dir_all(&signed_dir).map_err(|e| format!("Failed to create signed dir: {}", e))?;
    let tx_id = format!("tx_{}.json", chrono::Utc::now().timestamp_millis());
    let tx_path = signed_dir.join(&tx_id);
    let tmp_path = signed_dir.join(format!("{}.tmp", tx_id));
    let json = serde_json::to_string_pretty(tx).map_err(|e| format!("Failed to serialize tx: {}", e))?;
    fs::write(&tmp_path, &json).map_err(|e| format!("Failed to write tx tmp: {}", e))?;
    fs::rename(&tmp_path, &tx_path).map_err(|e| format!("Failed to rename tx: {}", e))?;
    Ok(tx_path.to_string_lossy().to_string())
}

/// FIX #5: canonicalize() each entry path and verify it's inside pending_dir
/// before reading. Prevents symlink traversal on Linux/macOS.
pub fn scan_pending_transactions(usb_path: &str) -> Result<Vec<serde_json::Value>, String> {
    let pending_dir = Path::new(usb_path).join("pending");
    if !pending_dir.exists() { return Ok(vec![]); }
    let canonical_pending = pending_dir.canonicalize()
        .map_err(|e| format!("Failed to canonicalize pending dir: {}", e))?;
    let mut transactions = vec![];
    let mut id_counter = 1;
    if let Ok(entries) = fs::read_dir(&pending_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            // FIX #5: resolve symlinks and verify the real path is inside pending_dir
            let canonical_path = match path.canonicalize() {
                Ok(p) => p,
                Err(_) => continue, // skip unresolvable entries (dangling symlinks)
            };
            if !canonical_path.starts_with(&canonical_pending) {
                continue; // path traversal attempt — skip silently
            }
            let content = fs::read_to_string(&canonical_path)
                .map_err(|e| format!("Failed to read tx: {}", e))?;
            let mut tx: serde_json::Value = serde_json::from_str(&content)
                .map_err(|e| format!("Failed to parse tx: {}", e))?;
            let path_str = path.to_string_lossy().to_string();
            tx["id"] = serde_json::json!(path_str);
            tx["path"] = serde_json::json!(path_str);
            tx["display_id"] = serde_json::json!(id_counter.to_string());
            transactions.push(tx);
            id_counter += 1;
        }
    }
    Ok(transactions)
}

/// FIX #5: same canonicalize check for signed transactions.
pub fn scan_signed_transactions(usb_path: &str) -> Result<Vec<serde_json::Value>, String> {
    let signed_dir = Path::new(usb_path).join("signed");
    if !signed_dir.exists() { return Ok(vec![]); }
    let canonical_signed = signed_dir.canonicalize()
        .map_err(|e| format!("Failed to canonicalize signed dir: {}", e))?;
    let mut transactions = vec![];
    let mut id_counter = 1;
    if let Ok(entries) = fs::read_dir(&signed_dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) != Some("json") {
                continue;
            }
            // FIX #5: resolve symlinks and verify the real path is inside signed_dir
            let canonical_path = match path.canonicalize() {
                Ok(p) => p,
                Err(_) => continue,
            };
            if !canonical_path.starts_with(&canonical_signed) {
                continue;
            }
            let content = fs::read_to_string(&canonical_path)
                .map_err(|e| format!("Failed to read tx: {}", e))?;
            let mut tx: serde_json::Value = serde_json::from_str(&content)
                .map_err(|e| format!("Failed to parse tx: {}", e))?;
            let path_str = path.to_string_lossy().to_string();
            tx["id"] = serde_json::json!(path_str);
            tx["path"] = serde_json::json!(path_str);
            tx["display_id"] = serde_json::json!(id_counter.to_string());
            transactions.push(tx);
            id_counter += 1;
        }
    }
    Ok(transactions)
}

/// Delete a pending transaction by its full file path (stored as `id` in scan results)
pub fn delete_pending_transaction(usb_path: &str, tx_id: &str) -> Result<(), String> {
    let pending_dir = Path::new(usb_path).join("pending");
    let target = Path::new(tx_id);
    // Security: ensure the path is inside the pending directory
    if !target.starts_with(&pending_dir) {
        return Err("Invalid transaction path: outside pending directory".to_string());
    }
    if target.exists() {
        fs::remove_file(target)
            .map_err(|e| format!("Failed to delete tx: {}", e))?;
    }
    Ok(())
}
