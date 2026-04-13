//! coldvault_core — PyO3-модуль для криптографического ядра ETH кошелька.
//!
//! Регистрирует Python-классы:
//!   - KeyManager     — генерация/импорт ключей, шифрование vault-файла
//!   - TransactionRequest — данные транзакции
//!   - TransactionSigner  — подпись EIP-1559 и Legacy транзакций
//!   - UsbManager     — безопасная работа с USB (path traversal защита)

use pyo3::prelude::*;

pub mod error;
pub mod key_manager;
pub mod transaction;
pub mod usb_manager;

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
