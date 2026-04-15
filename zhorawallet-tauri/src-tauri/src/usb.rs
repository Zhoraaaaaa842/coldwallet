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

    let drive_path = format!("{}:\\", drive_letter);
    let wide_path: Vec<u16> = OsStr::new(&drive_path)
        .encode_wide()
        .chain(Some(0))
        .collect();

    unsafe {
        // 1. Должен быть съёмный диск (DRIVE_REMOVABLE = 2)
        let drive_type = GetDriveTypeW(wide_path.as_ptr());
        if drive_type != 2 {
            return false;
        }

        // 2. Проверяем размер диска — флешка не может быть больше 256 GB
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
        // Больше 256 GB — точно не флешка
        if total_bytes > 274_877_906_944u64 {
            return false;
        }

        // 3. Проверяем тип шины через IOCTL_STORAGE_QUERY_PROPERTY
        // Открываем устройство \.\X:
        let device_path = format!("\\\\.\\{}:", drive_letter);
        let wide_device: Vec<u16> = OsStr::new(&device_path)
            .encode_wide()
            .chain(Some(0))
            .collect();

        let handle = CreateFileW(
            wide_device.as_ptr(),
            0, // no access needed for query
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            std::ptr::null_mut(),
            OPEN_EXISTING,
            0,
            std::ptr::null_mut(),
        );

        if handle == INVALID_HANDLE_VALUE {
            // Не смогли открыть — принимаем как USB если прошли проверку размера
            return true;
        }

        // STORAGE_PROPERTY_QUERY
        #[repr(C)]
        struct StoragePropertyQuery {
            property_id: u32,
            query_type: u32,
            additional_parameters: [u8; 1],
        }

        // STORAGE_DEVICE_DESCRIPTOR (нужен только BusType — offset 24)
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
            bus_type: u32, // BusTypeUsb = 7
            raw_properties_length: u32,
            raw_device_properties: [u8; 1],
        }

        let query = StoragePropertyQuery {
            property_id: 0, // StorageDeviceProperty
            query_type: 0,  // PropertyStandardQuery
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
            // Не смогли получить — доверяем проверке размера
            return true;
        }

        // BusTypeUsb = 7
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
        for drive in 'D'..='Z' {
            let path = format!("{}:\\", drive);
            if Path::new(&path).exists() && is_valid_usb_drive(drive) {
                return Some(path);
            }
        }
    }

    #[cfg(target_os = "linux")]
    {
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
