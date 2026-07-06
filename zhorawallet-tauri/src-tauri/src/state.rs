use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use zeroize::Zeroizing;
use crate::networks::Network;

/// Wallet runtime state.
/// NOTE: mnemonic is NOT stored here long-term — it is held transiently during
/// unlock and passed directly to crypto functions.
/// Wrapped in Zeroizing<String> so memory is securely wiped on drop.
#[derive(Debug, Serialize, Deserialize)]
pub struct WalletState {
    pub address: Option<String>,
    /// Mnemonic kept only while wallet is unlocked.
    /// Set to None when wallet is locked via lock_wallet command.
    /// Zeroizing<String> guarantees the memory is zeroed before dealloc,
    /// preventing dead-store-elimination that plagues manual memset approaches.
    #[serde(skip)]
    pub mnemonic: Option<Zeroizing<String>>,
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

impl WalletState {
    /// Securely clear sensitive data from memory when locking the wallet.
    /// Zeroizing<String> handles zeroing automatically on drop.
    pub fn lock(&mut self) {
        self.mnemonic = None; // Zeroizing<String> zeroes memory on drop
        self.is_locked = true;
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
