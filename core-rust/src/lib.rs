//! coldvault_core — PyO3-модуль для криптографического ядра ETH кошелька.
//!
//! Регистрирует Python-классы:
//!   - KeyManager     — генерация/импорт ключей, шифрование vault-файла
//!   - TransactionRequest — данные транзакции
//!   - TransactionSigner  — подпись EIP-1559 и Legacy транзакций

use pyo3::prelude::*;

mod error;        // маппинг Rust-ошибок → Python exceptions
mod key_manager;  // KeyManager
mod transaction;  // TransactionRequest + TransactionSigner
mod usb_manager;  // UsbManager (path traversal защита)

use key_manager::PyKeyManager;
use transaction::{PyTransactionRequest, PyTransactionSigner};
use usb_manager::PyUsbManager;

/// Инициализация Python-модуля `coldvault_core`.
#[pymodule]
fn coldvault_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyKeyManager>()?;
    m.add_class::<PyTransactionRequest>()?;
    m.add_class::<PyTransactionSigner>()?;
    m.add_class::<PyUsbManager>()?;
    Ok(())
}
