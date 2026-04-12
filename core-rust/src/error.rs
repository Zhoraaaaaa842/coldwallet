//! Маппинг Rust-ошибок в Python-исключения через PyO3.

use pyo3::exceptions::{
    PyPermissionError, PyRuntimeError, PyValueError,
};
use pyo3::PyErr;

/// Универсальный тип ошибки крейта.
#[derive(Debug)]
pub enum VaultError {
    /// Неверный пароль или повреждённый файл
    InvalidPassword(String),
    /// Блокировка после MAX_FAILED_ATTEMPTS попыток
    TooManyAttempts,
    /// Ошибка логики (ключ не загружен и т.д.)
    Logic(String),
    /// Ошибка ввода-вывода
    Io(std::io::Error),
    /// Ошибка криптографии
    Crypto(String),
    /// Path traversal попытка
    PathTraversal(String),
}

impl std::fmt::Display for VaultError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidPassword(m) => write!(f, "{m}"),
            Self::TooManyAttempts => write!(
                f,
                "Превышено максимальное число попыток. Перезапустите приложение."
            ),
            Self::Logic(m) => write!(f, "{m}"),
            Self::Io(e) => write!(f, "IO ошибка: {e}"),
            Self::Crypto(m) => write!(f, "Крипто-ошибка: {m}"),
            Self::PathTraversal(m) => write!(f, "Path traversal: {m}"),
        }
    }
}

impl std::error::Error for VaultError {}

/// Автоматическое преобразование VaultError → PyErr
impl From<VaultError> for PyErr {
    fn from(e: VaultError) -> PyErr {
        match e {
            VaultError::TooManyAttempts => PyPermissionError::new_err(e.to_string()),
            VaultError::InvalidPassword(m) => PyValueError::new_err(m),
            VaultError::PathTraversal(m) => PyPermissionError::new_err(m),
            VaultError::Logic(m) => PyRuntimeError::new_err(m),
            VaultError::Io(e) => PyRuntimeError::new_err(e.to_string()),
            VaultError::Crypto(m) => PyValueError::new_err(m),
        }
    }
}

impl From<std::io::Error> for VaultError {
    fn from(e: std::io::Error) -> Self {
        Self::Io(e)
    }
}
