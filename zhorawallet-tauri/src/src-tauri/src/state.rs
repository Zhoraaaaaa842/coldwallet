use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use crate::networks::Network;

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
#[allow(dead_code)]
pub struct UsbTransaction {
    pub id: String,
    pub path: String,
    pub data: serde_json::Value,
    pub status: String,
}

pub struct AppState {
    pub wallet: Mutex<WalletState>,
    pub usb_path: Mutex<Option<String>>,
    pub current_network: Mutex<Network>,
    pub price_cache: Mutex<f64>,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            wallet: Mutex::new(WalletState::default()),
            usb_path: Mutex::new(None),
            current_network: Mutex::new(Network::ethereum_mainnet()),
            price_cache: Mutex::new(0.0),
        }
    }
}
