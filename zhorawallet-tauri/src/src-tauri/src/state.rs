use serde::{Deserialize, Serialize};
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WalletState {
    pub address: Option<String>,
    pub mnemonic: Option<String>,
    pub is_initialized: bool,
    pub is_locked: bool,
    pub nonce: u64,
}

impl Default for WalletState {
    fn default() -> Self {
        Self {
            address: None,
            mnemonic: None,
            is_initialized: false,
            is_locked: true,
            nonce: 0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct UsbTransaction {
    pub id: String,
    pub path: String,
    pub data: serde_json::Value,
    pub status: String,
}

pub struct AppState {
    pub wallet: Mutex<WalletState>,
    pub usb_path: Mutex<Option<String>>,
    pub rpc_url: Mutex<String>,
    pub price_cache: Mutex<f64>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            wallet: Mutex::new(WalletState::default()),
            usb_path: Mutex::new(None),
            rpc_url: Mutex::new("https://eth.llamarpc.com".to_string()),
            price_cache: Mutex::new(0.0),
        }
    }
}
