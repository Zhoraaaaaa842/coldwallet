"""
ColdVault ETH — USB Storage Manager.
Обнаружение флешки, установка структуры кошелька, чтение/запись.
"""

import os
import sys
import json
import platform
import shutil
from pathlib import Path
from typing import Optional, List, Dict

# Структура папок на USB:
# /ColdVault/
# ├── wallet.vault        # Зашифрованный кошелёк
# ├── config.json         # Конфигурация (chain_id, метаданные)
# ├── pending/            # Неподписанные транзакции (от десктопа)
# └── signed/             # Подписанные транзакции (на десктоп)

VAULT_DIR = "ColdVault"
WALLET_FILE = "wallet.vault"
CONFIG_FILE = "config.json"
PENDING_DIR = "pending"
SIGNED_DIR = "signed"


class USBManager:
    """Управление файловой структурой кошелька на USB."""

    def __init__(self, usb_path: Optional[str] = None):
        self._usb_path = usb_path
        self._vault_path: Optional[Path] = None

        if usb_path:
            self._vault_path = Path(usb_path) / VAULT_DIR

    @property
    def vault_path(self) -> Optional[Path]:
        return self._vault_path

    @property
    def wallet_file(self) -> Optional[Path]:
        if self._vault_path:
            return self._vault_path / WALLET_FILE
        return None

    @property
    def is_initialized(self) -> bool:
        """Проверяет, установлен ли кошелёк на USB."""
        if not self._vault_path:
            return False
        return (
            self._vault_path.exists()
            and (self._vault_path / WALLET_FILE).exists()
        )

    @staticmethod
    def detect_usb_drives() -> List[Dict[str, str]]:
        """
        Обнаруживает подключённые USB-накопители.
        Возвращает список: [{"path": "/media/usb", "label": "MYUSB", "size": "16 GB"}]
        """
        drives = []
        system = platform.system()

        if system == "Windows":
            drives = USBManager._detect_windows()
        elif system == "Linux":
            drives = USBManager._detect_linux()
        elif system == "Darwin":
            drives = USBManager._detect_macos()

        return drives

    @staticmethod
    def _detect_windows() -> List[Dict[str, str]]:
        """Обнаружение USB на Windows через WMI или ctypes."""
        drives = []
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter_idx in range(26):
                if bitmask & (1 << letter_idx):
                    letter = chr(65 + letter_idx)
                    drive_path = f"{letter}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    # 2 = DRIVE_REMOVABLE
                    if drive_type == 2:
                        # Получаем метку тома
                        vol_name = ctypes.create_unicode_buffer(1024)
                        ctypes.windll.kernel32.GetVolumeInformationW(
                            drive_path, vol_name, 1024, None, None, None, None, 0
                        )
                        label = vol_name.value or f"USB ({letter}:)"

                        # Размер
                        free_bytes = ctypes.c_ulonglong(0)
                        total_bytes = ctypes.c_ulonglong(0)
                        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                            drive_path, None,
                            ctypes.pointer(total_bytes),
                            ctypes.pointer(free_bytes)
                        )
                        size_gb = total_bytes.value / (1024 ** 3)

                        drives.append({
                            "path": drive_path,
                            "label": label,
                            "size": f"{size_gb:.1f} GB",
                        })
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_linux() -> List[Dict[str, str]]:
        """Обнаружение USB на Linux через /proc/mounts."""
        drives = []
        mount_points = ["/media", "/mnt", "/run/media"]
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        device, mount = parts[0], parts[1]
                        if any(mount.startswith(mp) for mp in mount_points):
                            label = os.path.basename(mount)
                            try:
                                stat = os.statvfs(mount)
                                size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                                size_str = f"{size_gb:.1f} GB"
                            except Exception:
                                size_str = "N/A"

                            drives.append({
                                "path": mount,
                                "label": label,
                                "size": size_str,
                            })
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_macos() -> List[Dict[str, str]]:
        """Обнаружение USB на macOS через /Volumes."""
        drives = []
        volumes = Path("/Volumes")
        if volumes.exists():
            for vol in volumes.iterdir():
                if vol.is_dir() and vol.name != "Macintosh HD":
                    try:
                        stat = os.statvfs(str(vol))
                        size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                        # Фильтруем слишком большие (не USB)
                        if size_gb < 256:
                            drives.append({
                                "path": str(vol),
                                "label": vol.name,
                                "size": f"{size_gb:.1f} GB",
                            })
                    except Exception:
                        pass
        return drives

    def set_usb_path(self, path: str) -> None:
        """Устанавливает путь к USB."""
        if not os.path.isdir(path):
            raise ValueError(f"Путь не существует: {path}")
        self._usb_path = path
        self._vault_path = Path(path) / VAULT_DIR

    def initialize_usb(self) -> None:
        """
        Создаёт структуру ColdVault на USB.
        """
        if not self._vault_path:
            raise RuntimeError("USB путь не установлен")

        self._vault_path.mkdir(exist_ok=True)
        (self._vault_path / PENDING_DIR).mkdir(exist_ok=True)
        (self._vault_path / SIGNED_DIR).mkdir(exist_ok=True)

        # Конфигурация по умолчанию
        config = {
            "version": 1,
            "wallet_name": "ColdVault ETH",
            "chain_id": 1,
            "network": "Ethereum Mainnet",
            "created_at": self._get_timestamp(),
        }
        config_path = self._vault_path / CONFIG_FILE
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

    def save_pending_tx(self, tx_json: str, filename: str) -> Path:
        """Сохраняет неподписанную TX на USB для подписи."""
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")

        pending_path = self._vault_path / PENDING_DIR / filename
        with open(pending_path, "w", encoding="utf-8") as f:
            f.write(tx_json)
        return pending_path

    def save_signed_tx(self, raw_tx_hex: str, filename: str) -> Path:
        """Сохраняет подписанную TX на USB для broadcast."""
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")

        signed_data = {
            "type": "signed_transaction",
            "version": 1,
            "raw_tx": raw_tx_hex,
            "signed_at": self._get_timestamp(),
        }

        signed_path = self._vault_path / SIGNED_DIR / filename
        with open(signed_path, "w", encoding="utf-8") as f:
            json.dump(signed_data, f, indent=2)
        return signed_path

    def list_pending_txs(self) -> List[str]:
        """Список файлов неподписанных транзакций."""
        if not self._vault_path:
            return []
        pending_dir = self._vault_path / PENDING_DIR
        if not pending_dir.exists():
            return []
        return [f.name for f in pending_dir.glob("*.json")]

    def list_signed_txs(self) -> List[str]:
        """Список файлов подписанных транзакций."""
        if not self._vault_path:
            return []
        signed_dir = self._vault_path / SIGNED_DIR
        if not signed_dir.exists():
            return []
        return [f.name for f in signed_dir.glob("*.json")]

    def read_pending_tx(self, filename: str) -> str:
        """Читает неподписанную TX."""
        path = self._vault_path / PENDING_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def read_signed_tx(self, filename: str) -> Dict:
        """Читает подписанную TX."""
        path = self._vault_path / SIGNED_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_pending_tx(self, filename: str) -> None:
        """Удаляет обработанную pending TX."""
        path = self._vault_path / PENDING_DIR / filename
        if path.exists():
            path.unlink()

    def get_config(self) -> Dict:
        """Читает конфигурацию."""
        config_path = self._vault_path / CONFIG_FILE
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def update_config(self, updates: Dict) -> None:
        """Обновляет конфигурацию."""
        config = self.get_config()
        config.update(updates)
        config_path = self._vault_path / CONFIG_FILE
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
