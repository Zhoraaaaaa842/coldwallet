//! usb_manager.rs — безопасная работа с путями USB-носителей.
//!
//! Экспортирует в Python:
//!   safe_join_path(base, filename) -> str   — path traversal защита
//!   list_usb_wallet_files(base) -> list[str] — список .vault файлов
//!
//! Отличия от Python-версии:
//!   1. Path traversal защита через std::path canonicalize().
//!   2. Нет зависимостей на os.path — вся логика в std::path::Path.

use pyo3::prelude::*;
use pyo3::exceptions::{PyValueError, PyPermissionError, PyRuntimeError};
use std::path::{Path, PathBuf};

/// Безопасно объединяет base + filename, предотвращая path traversal атаки.
/// Вызывает PermissionError если filename выходит за пределы base.
///
/// Пример:
///   safe_join_path("/mnt/usb", "wallet.vault") -> "/mnt/usb/wallet.vault"
///   safe_join_path("/mnt/usb", "../../etc/passwd") -> PermissionError
#[pyfunction]
pub fn safe_join_path(base: &str, filename: &str) -> PyResult<String> {
    let base_path = Path::new(base);

    // Base должен существовать
    if !base_path.exists() {
        return Err(PyValueError::new_err(format!(
            "Базовый путь не существует: {base}"
        )));
    }

    // Filename не должен содержать компоненты пути (только имя файла)
    let filename_path = Path::new(filename);
    if filename_path.components().count() > 1 {
        return Err(PyPermissionError::new_err(
            "Path traversal запрещён: filename должен быть именем файла без директорий"
        ));
    }
    if filename.contains('/') || filename.contains('\\') || filename.contains("..") {
        return Err(PyPermissionError::new_err(
            "Path traversal запрещён: недопустимые символы в имени файла"
        ));
    }

    let joined = base_path.join(filename);

    // Если файл существует — проверяем через canonicalize
    if joined.exists() {
        let canonical = joined.canonicalize()
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка canonicalize: {e}")))?;
        let base_canonical = base_path.canonicalize()
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка canonicalize base: {e}")))?;

        if !canonical.starts_with(&base_canonical) {
            return Err(PyPermissionError::new_err(
                "Path traversal запрещён: файл выходит за пределы базового каталога"
            ));
        }
        Ok(canonical.to_string_lossy().to_string())
    } else {
        // Файл не существует: проверяем родительский каталог
        let base_canonical = base_path.canonicalize()
            .map_err(|e| PyRuntimeError::new_err(format!("Ошибка canonicalize base: {e}")))?;
        let expected = base_canonical.join(filename);
        Ok(expected.to_string_lossy().to_string())
    }
}

/// Возвращает список .vault файлов в директории base.
/// Не рекурсивный, только верхний уровень директории.
#[pyfunction]
pub fn list_usb_wallet_files(base: &str) -> PyResult<Vec<String>> {
    let base_path = Path::new(base);
    if !base_path.is_dir() {
        return Err(PyValueError::new_err(format!(
            "Директория не существует: {base}"
        )));
    }

    let mut files = Vec::new();
    let entries = std::fs::read_dir(base_path)
        .map_err(|e| PyRuntimeError::new_err(format!("Ошибка чтения директории: {e}")))?;

    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_file() {
            if let Some(ext) = path.extension() {
                if ext == "vault" {
                    if let Some(name) = path.file_name() {
                        files.push(name.to_string_lossy().to_string());
                    }
                }
            }
        }
    }

    files.sort(); // детерминированный порядок
    Ok(files)
}
