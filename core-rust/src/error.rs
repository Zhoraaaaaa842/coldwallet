//! Маппинг Rust-ошибок в Python-исключения через PyO3.

use pyo3::exceptions::{
    PyIOError, PyPermissionError, PyRuntimeError, PyValueError,
};
use pyo3::PyErr;

#[derive(Debug)]
pub enum VaultError {
    InvalidPassword(String),
    TooManyAttempts,
    Logic(String),
    Io(std::io::Error),
    /// FIX: добавлен отдельный вариант CryptoError вместо Logic
    /// — иначе Python получал RuntimeError на крипто-ошибках вместо ValueError
    Crypto(String),
    PathTraversal(String),
}

impl std::fmt::Display for VaultError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidPassword(m) => write!(f, "{m}"),
            Self::TooManyAttempts =>
                write!(f, "Превышено максимальное число попыток."),
            Self::Logic(m) => write!(f, "{m}"),
            Self::Io(e) => write!(f, "IO: {e}"),
            Self::Crypto(m) => write!(f, "Крипто: {m}"),
            Self::PathTraversal(m) => write!(f, "PathTraversal: {m}"),
        }
    }
}

impl std::error::Error for VaultError {}

impl From<VaultError> for PyErr {
    fn from(e: VaultError) -> PyErr {
        match e {
            VaultError::TooManyAttempts =>
                PyPermissionError::new_err(e.to_string()),
            VaultError::InvalidPassword(m) =>
                PyValueError::new_err(m),
            VaultError::PathTraversal(m) =>
                PyPermissionError::new_err(m),
            VaultError::Logic(m) =>
                PyRuntimeError::new_err(m),
            // FIX: Io → PyIOError (было PyRuntimeError — неправильно)
            VaultError::Io(e) =>
                PyIOError::new_err(e.to_string()),
            // FIX: Crypto → PyValueError (было PyRuntimeError)
            VaultError::Crypto(m) =>
                PyValueError::new_err(m),
        }
    }
}

impl From<std::io::Error> for VaultError {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e)
    }
}
