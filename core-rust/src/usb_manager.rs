//! Безопасная работа с USB-хранилищем для vault-файлов.
//!
//! Защита от path traversal: все пути разрешаются относительно
//! базового каталога USB-устройства и проверяются на выход за его пределы.

use std::path::{Path, PathBuf};

use pyo3::prelude::*;

use crate::error::VaultError;

/// Менеджер USB-хранилища с защитой от path traversal.
///
/// Пример из Python:
/// ```python
/// from coldvault_core import UsbManager
/// usb = UsbManager("/media/usb0")
/// safe_path = usb.safe_path("wallet.vault")
/// ```
#[pyclass(name = "UsbManager")]
pub struct PyUsbManager {
    /// Абсолютный канонический путь к корню USB-устройства
    base_dir: PathBuf,
}

#[pymethods]
impl PyUsbManager {
    /// Инициализирует UsbManager с базовым каталогом.
    /// Вызывает ошибку если каталог не существует или не является директорией.
    #[new]
    pub fn new(base_path: &str) -> PyResult<Self> {
        let base = Path::new(base_path)
            .canonicalize()
            .map_err(|e| VaultError::Io(e))?;

        if !base.is_dir() {
            return Err(VaultError::Logic(format!(
                "{base_path} не является директорией"
            ))
            .into());
        }

        Ok(Self { base_dir: base })
    }

    /// Возвращает абсолютный путь к файлу внутри базового каталога.
    ///
    /// Защита от path traversal:
    /// - Запрещает ../  и абсолютные пути в filename
    /// - Проверяет что resolved путь начинается с base_dir
    pub fn safe_path(&self, filename: &str) -> PyResult<String> {
        // Запрещаем абсолютные пути и компоненты ..
        let p = Path::new(filename);
        if p.is_absolute() {
            return Err(VaultError::PathTraversal(
                "Абсолютный путь запрещён".into(),
            )
            .into());
        }
        for component in p.components() {
            use std::path::Component;
            if matches!(component, Component::ParentDir) {
                return Err(VaultError::PathTraversal(
                    "Path traversal (.. ) запрещён".into(),
                )
                .into());
            }
        }

        let resolved = self.base_dir.join(p);

        // Дополнительная проверка через canonicalize (если файл уже существует)
        let check_path = if resolved.exists() {
            resolved
                .canonicalize()
                .map_err(|e| VaultError::Io(e))?
        } else {
            // Файл ещё не существует — проверяем родительский каталог
            let parent = resolved.parent().unwrap_or(&self.base_dir);
            let canon_parent = parent
                .canonicalize()
                .map_err(|e| VaultError::Io(e))?;
            canon_parent.join(resolved.file_name().unwrap_or_default())
        };

        // Проверяем что путь внутри base_dir
        if !check_path.starts_with(&self.base_dir) {
            return Err(VaultError::PathTraversal(format!(
                "Путь выходит за пределы USB: {}",
                check_path.display()
            ))
            .into());
        }

        check_path
            .to_str()
            .map(|s| s.to_string())
            .ok_or_else(|| {
                VaultError::Logic("Путь содержит не-UTF8 символы".into()).into()
            })
    }

    /// Возвращает базовый каталог USB.
    #[getter]
    pub fn base_dir(&self) -> String {
        self.base_dir.display().to_string()
    }

    /// Проверяет существование vault-файла на USB.
    pub fn vault_exists(&self, filename: &str) -> PyResult<bool> {
        let path = self.safe_path(filename)?;
        Ok(Path::new(&path).exists())
    }

    /// Возвращает список .vault файлов в корне USB.
    pub fn list_vaults(&self) -> PyResult<Vec<String>> {
        let mut vaults = Vec::new();
        let entries = std::fs::read_dir(&self.base_dir)
            .map_err(VaultError::Io)?;
        for entry in entries.flatten() {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("vault") {
                if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                    vaults.push(name.to_string());
                }
            }
        }
        Ok(vaults)
    }
}
