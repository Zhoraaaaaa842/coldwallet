"""
ZhoraWallet ETH — USB Storage Manager.
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
# ├── config.json         # Конфигурация
# ├── pending/            # Неподписанные транзакции
# └── signed/             # Подписанные транзакции

VAULT_DIR   = "ColdVault"
WALLET_FILE = "wallet.vault"
CONFIG_FILE = "config.json"
PENDING_DIR = "pending"
SIGNED_DIR  = "signed"

# Типы дисков Windows, которые считаются USB-носителями
# 2 = DRIVE_REMOVABLE (классические USB)
# 3 = DRIVE_FIXED     (некоторые флешки и внешние SSD определяются так)
USB_DRIVE_TYPES_WINDOWS = {2, 3}


class USBManager:
    """Управление файловой структурой кошелька на USB."""

    def __init__(self, usb_path: Optional[str] = None):
        self._usb_path = usb_path
        self._vault_path: Optional[Path] = None
        if usb_path:
            self._vault_path = Path(usb_path) / VAULT_DIR

    # ─── Проперти ───

    @property
    def vault_path(self) -> Optional[Path]:
        return self._vault_path

    @property
    def wallet_file(self) -> Optional[Path]:
        return (self._vault_path / WALLET_FILE) if self._vault_path else None

    @property
    def is_initialized(self) -> bool:
        if not self._vault_path:
            return False
        return (
            self._vault_path.exists()
            and (self._vault_path / WALLET_FILE).exists()
        )

    # ─── Обнаружение USB ───

    @staticmethod
    def detect_usb_drives() -> List[Dict[str, str]]:
        """
        Обнаруживает подключённые USB-накопители.
        Возвращает [{"path": ..., "label": ..., "size": ...}]
        """
        system = platform.system()
        try:
            if system == "Windows":
                drives = USBManager._detect_windows()
            elif system == "Linux":
                drives = USBManager._detect_linux()
            elif system == "Darwin":
                drives = USBManager._detect_macos()
            else:
                drives = []
        except Exception:
            drives = []

        # Если ctypes/proc не сработали — пробуем psutil
        if not drives:
            drives = USBManager._detect_psutil()

        return drives

    @staticmethod
    def _detect_windows() -> List[Dict[str, str]]:
        """Детекция USB на Windows через ctypes."""
        drives = []
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter_idx in range(26):
                if not (bitmask & (1 << letter_idx)):
                    continue
                letter = chr(65 + letter_idx)
                drive_path = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)

                # 2 = DRIVE_REMOVABLE, 3 = DRIVE_FIXED (некоторые USB)
                if drive_type not in USB_DRIVE_TYPES_WINDOWS:
                    continue

                # Пропускаем C:\ (системный диск)
                if letter == "C":
                    continue

                # Метка тома
                vol_name = ctypes.create_unicode_buffer(1024)
                ctypes.windll.kernel32.GetVolumeInformationW(
                    drive_path, vol_name, 1024,
                    None, None, None, None, 0
                )
                label = vol_name.value or f"USB ({letter}:)"

                # Размер
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    drive_path, None,
                    ctypes.pointer(total_bytes),
                    None
                )
                size_gb = total_bytes.value / (1024 ** 3)

                # Игнорируем диски > 2 TB (вряд ли это USB)
                if size_gb > 2048:
                    continue

                drives.append({
                    "path": drive_path,
                    "label": label,
                    "size": f"{size_gb:.1f} GB",
                    "type": str(drive_type),
                })
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_linux() -> List[Dict[str, str]]:
        """Детекция USB на Linux через /proc/mounts."""
        drives = []
        mount_points = ["/media", "/mnt", "/run/media"]
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    device, mount = parts[0], parts[1]
                    if not any(mount.startswith(mp) for mp in mount_points):
                        continue
                    label = os.path.basename(mount)
                    try:
                        stat = os.statvfs(mount)
                        size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                        size_str = f"{size_gb:.1f} GB"
                    except Exception:
                        size_str = "N/A"
                    drives.append({"path": mount, "label": label, "size": size_str})
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_macos() -> List[Dict[str, str]]:
        """Детекция USB на macOS через /Volumes."""
        drives = []
        volumes = Path("/Volumes")
        if not volumes.exists():
            return drives
        for vol in volumes.iterdir():
            if not vol.is_dir() or vol.name == "Macintosh HD":
                continue
            try:
                stat = os.statvfs(str(vol))
                size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                if 0 < size_gb < 256:
                    drives.append({
                        "path": str(vol),
                        "label": vol.name,
                        "size": f"{size_gb:.1f} GB",
                    })
            except Exception:
                pass
        return drives

    @staticmethod
    def _detect_psutil() -> List[Dict[str, str]]:
        """Фоллбэк через psutil — работает на всех ОС."""
        drives = []
        try:
            import psutil
            for part in psutil.disk_partitions(all=False):
                # Фильтр: removable или не системный диск
                opts = part.opts.lower()
                is_removable = "removable" in opts
                is_system = part.mountpoint in ("/", "C:\\", "/boot", "/boot/efi")
                if is_system:
                    continue
                # на Windows берём все не-C: диски < 2TB
                # на Linux/macOS берём только отмонтированные в /media, /mnt, /Volumes
                if not is_removable:
                    mp = part.mountpoint
                    valid_prefixes = ("/media", "/mnt", "/run/media", "/Volumes")
                    if platform.system() == "Windows":
                        if part.mountpoint.startswith("C:"):
                            continue
                    elif not any(mp.startswith(p) for p in valid_prefixes):
                        continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    size_gb = usage.total / (1024 ** 3)
                    if size_gb > 2048:
                        continue
                    label = os.path.basename(part.mountpoint) or part.device
                    drives.append({
                        "path": part.mountpoint,
                        "label": label or f"USB ({part.mountpoint})",
                        "size": f"{size_gb:.1f} GB",
                    })
                except Exception:
                    pass
        except ImportError:
            pass
        return drives

    # ─── Установка и инициализация ───

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

        self._vault_path.mkdir(parents=True, exist_ok=True)
        (self._vault_path / PENDING_DIR).mkdir(parents=True, exist_ok=True)
        (self._vault_path / SIGNED_DIR).mkdir(parents=True, exist_ok=True)

        config = {
            "version": 1,
            "wallet_name": "ZhoraWallet ETH",
            "chain_id": 1,
            "network": "Ethereum Mainnet",
            "created_at": self._get_timestamp(),
        }
        config_path = self._vault_path / CONFIG_FILE
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

    @staticmethod
    def ensure_dist_dir() -> Path:
        """
        Гарантирует существование папки dist/ в корне проекта.
        Возвращает Path к dist/.
        """
        root = Path(__file__).resolve().parent.parent.parent
        dist = root / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        return dist

    # ─── Чтение / запись ───

    def save_pending_tx(self, tx_json: str, filename: str) -> Path:
        """Сохраняет неподписанную TX на USB."""
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")
        pending_path = self._vault_path / PENDING_DIR / filename
        with open(pending_path, "w", encoding="utf-8") as f:
            f.write(tx_json)
        return pending_path

    def save_signed_tx(self, raw_tx_hex: str, filename: str) -> Path:
        """Сохраняет подписанную TX на USB."""
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
            json.dump(signed_data, f, indent=2, ensure_ascii=False)
        return signed_path

    def list_pending_txs(self) -> List[str]:
        """Список файлов неподписанных TX."""
        if not self._vault_path:
            return []
        pending_dir = self._vault_path / PENDING_DIR
        if not pending_dir.exists():
            return []
        return [f.name for f in pending_dir.glob("*.json")]

    def list_signed_txs(self) -> List[str]:
        """Список файлов подписанных TX."""
        if not self._vault_path:
            return []
        signed_dir = self._vault_path / SIGNED_DIR
        if not signed_dir.exists():
            return []
        return [f.name for f in signed_dir.glob("*.json")]

    def read_pending_tx(self, filename: str) -> str:
        path = self._vault_path / PENDING_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def read_signed_tx(self, filename: str) -> Dict:
        path = self._vault_path / SIGNED_DIR / filename
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_pending_tx(self, filename: str) -> None:
        path = self._vault_path / PENDING_DIR / filename
        if path.exists():
            path.unlink()

    def get_config(self) -> Dict:
        config_path = self._vault_path / CONFIG_FILE
        if config_path and config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def update_config(self, updates: Dict) -> None:
        config = self.get_config()
        config.update(updates)
        config_path = self._vault_path / CONFIG_FILE
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
