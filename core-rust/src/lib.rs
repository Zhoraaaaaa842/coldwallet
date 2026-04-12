//! coldvault_core — Rust-ядро ETH холодного кошелька.
//! Регистрирует Python-модуль через PyO3.
//!
//! Структура:
//!   key_manager  — генерация ключей, BIP-39/44, AES-256-GCM шифрование
//!   transaction  — подпись транзакций (EIP-1559, Legacy)
//!   usb_manager  — безопасная работа с путями USB-носителей

mod key_manager;
mod transaction;
mod usb_manager;

use pyo3::prelude::*;

/// Точка входа PyO3.  
/// Python-код: `import coldvault_core`
#[pymodule]
fn coldvault_core(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // ── Классы из key_manager ──────────────────────────────────────────────
    m.add_class::<key_manager::KeyManager>()?;

    // ── Классы из transaction ─────────────────────────────────────────────
    m.add_class::<transaction::TransactionRequest>()?;
    m.add_class::<transaction::TransactionSigner>()?;

    // ── Функции из usb_manager ────────────────────────────────────────────
    m.add_function(wrap_pyfunction!(usb_manager::safe_join_path, m)?)?;
    m.add_function(wrap_pyfunction!(usb_manager::list_usb_wallet_files, m)?)?;

    // ── Версия модуля ─────────────────────────────────────────────────────
    m.add("__version__", "0.1.0")?;

    Ok(())
}
