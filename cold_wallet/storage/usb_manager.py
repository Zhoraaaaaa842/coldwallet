"""
ZhoraWallet ETH — USB Storage Manager.
Обнаружение флешки, установка структуры кошелька, чтение/запись.
"""

import os
import json
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

VAULT_DIR   = "ColdVault"
WALLET_FILE = "wallet.vault"
CONFIG_FILE = "config.json"
PENDING_DIR = "pending"
SIGNED_DIR  = "signed"


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
        return (self._vault_path / WALLET_FILE) if self._vault_path else None

    @property
    def is_initialized(self) -> bool:
        if not self._vault_path:
            return False
        return (
            self._vault_path.exists()
            and (self._vault_path / WALLET_FILE).exists()
        )

    # ------------------------------------------------------------------ #
    #  FIX #2: Path Traversal защита                                       #
    # ------------------------------------------------------------------ #
    def _safe_path(self, base_dir: Path, filename: str) -> Path:
        """
        Проверяет что filename не выходит за пределы base_dir.
        Защита от path traversal атак (../../etc/passwd и т.п.).
        """
        resolved = (base_dir / filename).resolve()
        base_resolved = base_dir.resolve()
        if not str(resolved).startswith(str(base_resolved) + os.sep) \
                and resolved != base_resolved:
            raise ValueError(f"Недопустимый путь к файлу: {filename}")
        return resolved

    @staticmethod
    def detect_usb_drives() -> List[Dict[str, str]]:
        system = platform.system()
        if system == "Windows":
            return USBManager._detect_windows()
        elif system == "Linux":
            return USBManager._detect_linux()
        elif system == "Darwin":
            return USBManager._detect_macos()
        return []

    @staticmethod
    def _detect_windows() -> List[Dict[str, str]]:
        drives = []
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for letter_idx in range(26):
                if bitmask & (1 << letter_idx):
                    letter = chr(65 + letter_idx)
                    drive_path = f"{letter}:\\"
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                    if drive_type == 2:  # DRIVE_REMOVABLE
                        vol_name = ctypes.create_unicode_buffer(1024)
                        ctypes.windll.kernel32.GetVolumeInformationW(
                            drive_path, vol_name, 1024, None, None, None, None, 0
                        )
                        label = vol_name.value or f"USB ({letter}:)"
                        free_bytes  = ctypes.c_ulonglong(0)
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
        drives = []
        mount_points = ("/media", "/mnt", "/run/media")
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
                            drives.append({"path": mount, "label": label, "size": size_str})
        except Exception:
            pass
        return drives

    @staticmethod
    def _detect_macos() -> List[Dict[str, str]]:
        """
        FIX #7: Используем diskutil для фильтрации только физических
        съёмных носителей. Сетевые диски и Time Machine исключены.
        """
        drives = []
        try:
            result = subprocess.run(
                ["diskutil", "list", "-plist", "external"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("diskutil failed")

            import plistlib
            plist = plistlib.loads(result.stdout.encode())
            disk_ids = plist.get("AllDisksAndPartitions", [])

            for disk in disk_ids:
                disk_id = disk.get("DeviceIdentifier", "")
                # Пропускаем разделы, берём только целые диски
                if not disk_id or "s" in disk_id.split("disk")[-1]:
                    continue
                mount = disk.get("MountPoint", "")
                if not mount or not os.path.isdir(mount):
                    continue
                label = os.path.basename(mount) or disk_id
                try:
                    stat = os.statvfs(mount)
                    size_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
                    size_str = f"{size_gb:.1f} GB"
                except Exception:
                    size_str = "N/A"
                drives.append({"path": mount, "label": label, "size": size_str})
        except Exception:
            # Fallback: старый метод через /Volumes если diskutil недоступен
            volumes = Path("/Volumes")
            if volumes.exists():
                for vol in volumes.iterdir():
                    if vol.is_dir() and vol.name not in ("Macintosh HD", "Preboot", "Recovery", "VM"):
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

    def set_usb_path(self, path: str) -> None:
        if not os.path.isdir(path):
            raise ValueError(f"Путь не существует: {path}")
        self._usb_path = path
        self._vault_path = Path(path) / VAULT_DIR

    def initialize_usb(self) -> None:
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
        root = Path(__file__).resolve().parent.parent.parent
        dist = root / "dist"
        dist.mkdir(parents=True, exist_ok=True)
        return dist

    def save_pending_tx(self, tx_json: str, filename: str) -> Path:
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")
        p = self._safe_path(self._vault_path / PENDING_DIR, filename)
        p.write_text(tx_json, encoding="utf-8")
        return p

    def save_signed_tx(self, raw_tx_hex: str, filename: str) -> Path:
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")
        data = {
            "type": "signed_transaction",
            "version": 1,
            "raw_tx": raw_tx_hex,
            "signed_at": self._get_timestamp(),
        }
        p = self._safe_path(self._vault_path / SIGNED_DIR, filename)
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
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")
        # FIX #2: path traversal защита
        p = self._safe_path(self._vault_path / PENDING_DIR, filename)
        return p.read_text(encoding="utf-8")

    def read_signed_tx(self, filename: str) -> Dict:
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")
        # FIX #2: path traversal защита
        p = self._safe_path(self._vault_path / SIGNED_DIR, filename)
        return json.loads(p.read_text(encoding="utf-8"))

    def delete_pending_tx(self, filename: str) -> None:
        if not self._vault_path:
            raise RuntimeError("USB не инициализирован")
        p = self._safe_path(self._vault_path / PENDING_DIR, filename)
        if p.exists():
            p.unlink()

    def get_config(self) -> Dict:
        if not self._vault_path:
            return {}
        p = self._vault_path / CONFIG_FILE
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def update_config(self, updates: Dict) -> None:
        if not self._vault_path:
            raise RuntimeError("USB путь не установлен")
        config = self.get_config()
        config.update(updates)
        (self._vault_path / CONFIG_FILE).write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
