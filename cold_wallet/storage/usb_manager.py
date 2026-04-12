"""
ZhoraWallet ETH — Storage Manager.
Обнаружение внешних USB/HDD-носителей, установка структуры кошелька, чтение/запись.
Поддерживает USB-флешки, внешние HDD/SSD любого размера.
"""

import os
import json
import platform
from pathlib import Path
from typing import Optional, List, Dict

VAULT_DIR   = "ColdVault"
WALLET_FILE = "wallet.vault"
CONFIG_FILE = "config.json"
PENDING_DIR = "pending"
SIGNED_DIR  = "signed"

# Системные буквы Windows, которые никогда не являются внешними носителями
_WINDOWS_SYSTEM_LETTERS = {"C"}

# Системные точки монтирования Linux/macOS
_SYSTEM_MOUNTS = {"/", "/boot", "/boot/efi", "/home", "/usr", "/var", "/tmp", "/sys", "/proc"}


class USBManager:
    """
    Управление файловой структурой кошелька на внешнем носителе.
    Работает с USB-флешками и внешними HDD/SSD любого размера.
    """

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

    # ─── Обнаружение дисков ───

    @staticmethod
    def detect_usb_drives() -> List[Dict[str, str]]:
        """
        Обнаруживает внешние носители: USB-флешки и внешние HDD/SSD.
        Возвращает [{"path": ..., "label": ..., "size": ..., "kind": ...}]
        """
        system = platform.system()
        drives = []
        try:
            if system == "Windows":
                drives = USBManager._detect_windows()
            elif system == "Linux":
                drives = USBManager._detect_linux()
            elif system == "Darwin":
                drives = USBManager._detect_macos()
        except Exception:
            pass

        # Фоллбэк: psutil если основной метод не нашёл ничего
        if not drives:
            drives = USBManager._detect_psutil()

        return drives

    @staticmethod
    def _detect_windows() -> List[Dict[str, str]]:
        """
        Windows: принимаем все диски кроме системных (C:).
        Типы:
          2 = DRIVE_REMOVABLE  — классические USB-флешки
          3 = DRIVE_FIXED      — внешние HDD/SSD, некоторые USB-носители
        """
        drives = []
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter_idx in range(26):
                if not (bitmask & (1 << letter_idx)):
                    continue
                letter = chr(65 + letter_idx)

                # Системные буквы — скип
                if letter in _WINDOWS_SYSTEM_LETTERS:
                    continue

                drive_path = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)

                # Принимаем REMOVABLE (2) и FIXED (3)
                # CDROM(5), RAMDISK(6), UNKNOWN(0), NO_ROOT(1), REMOTE(4) — игнорируем
                if drive_type not in (2, 3):
                    continue

                # Метка тома
                vol_name = ctypes.create_unicode_buffer(1024)
                ctypes.windll.kernel32.GetVolumeInformationW(
                    drive_path, vol_name, 1024,
                    None, None, None, None, 0
                )
                label = vol_name.value or f"Диск ({letter}:)"

                # Размер
                total_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    drive_path, None,
                    ctypes.pointer(total_bytes),
                    None
                )
                size_gb = total_bytes.value / (1024 ** 3)
                if size_gb == 0:
                    continue

                kind = "USB" if drive_type == 2 else "HDD/SSD"
                drives.append({
                    "path": drive_path,
                    "label": label,
                    "size": f"{size_gb:.1f} GB",
                    "kind": kind,
                })
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_linux() -> List[Dict[str, str]]:
        """
        Linux: сканируем /proc/mounts.
        Берём /media, /mnt, /run/media — туда монтируются все внешние носители.
        """
        drives = []
        mount_points = ("/media", "/mnt", "/run/media")
        try:
            with open("/proc/mounts", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    device, mount = parts[0], parts[1]
                    if not any(mount.startswith(mp) for mp in mount_points):
                        continue
                    label = os.path.basename(mount) or device
                    try:
                        stat = os.statvfs(mount)
                        size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                        size_str = f"{size_gb:.1f} GB"
                    except Exception:
                        size_str = "N/A"
                    # Определяем тип по устройству (sdа = HDD/USB, sdа* = раздел)
                    kind = "HDD/SSD" if "/sd" in device else "USB"
                    drives.append({
                        "path": mount,
                        "label": label,
                        "size": size_str,
                        "kind": kind,
                    })
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_macos() -> List[Dict[str, str]]:
        """
        macOS: сканируем /Volumes.
        Берём всё кроме системных томов (без лимита по размеру).
        """
        drives = []
        system_volumes = {"Macintosh HD", "Macintosh HD - Data", "Preboot", "Recovery", "VM"}
        volumes = Path("/Volumes")
        if not volumes.exists():
            return drives
        for vol in volumes.iterdir():
            if not vol.is_dir() or vol.name in system_volumes:
                continue
            try:
                stat = os.statvfs(str(vol))
                size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                if size_gb <= 0:
                    continue
                kind = "HDD/SSD" if size_gb > 64 else "USB"
                drives.append({
                    "path": str(vol),
                    "label": vol.name,
                    "size": f"{size_gb:.1f} GB",
                    "kind": kind,
                })
            except Exception:
                pass
        return drives

    @staticmethod
    def _detect_psutil() -> List[Dict[str, str]]:
        """
        Фоллбэк через psutil — работает на всех ОС.
        Принимает все несистемные диски без ограничения по размеру.
        """
        drives = []
        try:
            import psutil
            sys_name = platform.system()
            for part in psutil.disk_partitions(all=False):
                mp = part.mountpoint

                # Скипаем системные точки монтирования
                if mp in _SYSTEM_MOUNTS:
                    continue
                if sys_name == "Windows" and mp.upper().startswith("C:"):
                    continue

                # На Linux/macOS берём только внешние точки монтирования
                if sys_name != "Windows":
                    valid = ("/media", "/mnt", "/run/media", "/Volumes")
                    if not any(mp.startswith(p) for p in valid):
                        continue

                try:
                    usage = psutil.disk_usage(mp)
                    size_gb = usage.total / (1024 ** 3)
                    if size_gb <= 0:
                        continue
                    label = os.path.basename(mp) or part.device or mp
                    kind = "HDD/SSD" if size_gb > 64 else "USB"
                    drives.append({
                        "path": mp,
                        "label": label,
                        "size": f"{size_gb:.1f} GB",
                        "kind": kind,
                    })
                except Exception:
                    pass
        except ImportError:
            pass
        return drives

    # ─── Установка ───

    def set_usb_path(self, path: str) -> None:
        """Устанавливает путь к носителю."""
        if not os.path.isdir(path):
            raise ValueError(f"Путь не существует: {path}")
        self._usb_path = path
        self._vault_path = Path(path) / VAULT_DIR

    def initialize_usb(self) -> None:
        """Создаёт структуру ColdVault на носителе."""
        if not self._vault_path:
            raise RuntimeError("Путь к носителю не установлен")

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
        """Гарантирует существование dist/ в корне проекта."""
        root = Path(__file__).resolve().parent.parent.parent
        dist = root / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        return dist

    # ─── Чтение / запись ───

    def save_pending_tx(self, tx_json: str, filename: str) -> Path:
        if not self._vault_path:
            raise RuntimeError("USB/HDD не инициализирован")
        p = self._vault_path / PENDING_DIR / filename
        p.write_text(tx_json, encoding="utf-8")
        return p

    def save_signed_tx(self, raw_tx_hex: str, filename: str) -> Path:
        if not self._vault_path:
            raise RuntimeError("USB/HDD не инициализирован")
        data = {
            "type": "signed_transaction",
            "version": 1,
            "raw_tx": raw_tx_hex,
            "signed_at": self._get_timestamp(),
        }
        p = self._vault_path / SIGNED_DIR / filename
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    def list_pending_txs(self) -> List[str]:
        if not self._vault_path:
            return []
        d = self._vault_path / PENDING_DIR
        return [f.name for f in d.glob("*.json")] if d.exists() else []

    def list_signed_txs(self) -> List[str]:
        if not self._vault_path:
            return []
        d = self._vault_path / SIGNED_DIR
        return [f.name for f in d.glob("*.json")] if d.exists() else []

    def read_pending_tx(self, filename: str) -> str:
        return (self._vault_path / PENDING_DIR / filename).read_text(encoding="utf-8")

    def read_signed_tx(self, filename: str) -> Dict:
        return json.loads((self._vault_path / SIGNED_DIR / filename).read_text(encoding="utf-8"))

    def delete_pending_tx(self, filename: str) -> None:
        p = self._vault_path / PENDING_DIR / filename
        if p.exists():
            p.unlink()

    def get_config(self) -> Dict:
        p = self._vault_path / CONFIG_FILE
        return json.loads(p.read_text(encoding="utf-8")) if p and p.exists() else {}

    def update_config(self, updates: Dict) -> None:
        config = self.get_config()
        config.update(updates)
        (self._vault_path / CONFIG_FILE).write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
