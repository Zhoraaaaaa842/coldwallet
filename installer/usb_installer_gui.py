"""
ColdVault ETH — USB Installer GUI

Графический установщик холодного кошелька на флешку.

Что делает:
1. Обнаруживает USB-накопители
2. Показывает GUI с предупреждением о форматировании
3. Форматирует флешку (NTFS)
4. Устанавливает SignOffline.exe + структуру ColdVault
5. Создаёт autorun.inf, launch.bat, README.txt

Собирается в UsbInstaller.exe через PyInstaller.
"""

import os
import sys
import json
import shutil
import ctypes
import platform
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

# ─── Убедимся что пакеты проекта найдены ─── #
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

sys.path.insert(0, str(BASE_DIR))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar, QTextEdit,
    QFrame, QMessageBox, QCheckBox, QGroupBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette


# ══════════════════════════════════════════════
#  Вспомогательные функции
# ══════════════════════════════════════════════

def is_admin() -> bool:
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0


def detect_usb_drives() -> list[dict]:
    """Обнаружение USB-накопителей."""
    drives = []
    if platform.system() == "Windows":
        try:
            import wmi
            c = wmi.WMI()
            for disk in c.Win32_LogicalDisk(DriveType=2):
                size_gb = int(disk.Size or 0) / (1024 ** 3)
                drives.append({
                    "path": disk.DeviceID + "\\",
                    "label": disk.VolumeName or f"USB ({disk.DeviceID})",
                    "size": f"{size_gb:.1f} GB",
                    "letter": disk.DeviceID.rstrip(":"),
                })
        except ImportError:
            # Fallback без wmi
            import string
            for letter in string.ascii_uppercase:
                path = f"{letter}:\\"
                if os.path.exists(path):
                    drive_type = ctypes.windll.kernel32.GetDriveTypeW(path)
                    if drive_type == 2:  # DRIVE_REMOVABLE
                        total = ctypes.c_ulonglong(0)
                        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                            path, None, ctypes.byref(total), None
                        )
                        size_gb = total.value / (1024 ** 3)
                        drives.append({
                            "path": path,
                            "label": f"USB ({letter}:)",
                            "size": f"{size_gb:.1f} GB",
                            "letter": letter,
                        })
    return drives


def format_windows(letter: str, label: str = "COLDVAULT") -> tuple[bool, str]:
    drive = letter.rstrip("\\").rstrip(":")
    cmd = f"format {drive}: /FS:NTFS /V:{label} /Q /Y"
    try:
        proc = subprocess.Popen(
            cmd, shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=b"\n", timeout=180)
        if proc.returncode == 0:
            return True, "Форматирование завершено"
        out = (stdout + stderr).decode("cp866", errors="replace")
        return False, f"Ошибка: {out[:300]}"
    except subprocess.TimeoutExpired:
        proc.kill()
        return False, "Таймаут форматирования"
    except Exception as e:
        return False, str(e)


def install_coldvault_structure(usb_path: str, sign_exe_path: str = None) -> list[str]:
    """Создаёт структуру ColdVault. Возвращает список действий."""
    log = []
    vault_dir = Path(usb_path) / "ColdVault"
    vault_dir.mkdir(exist_ok=True)
    (vault_dir / "pending").mkdir(exist_ok=True)
    (vault_dir / "signed").mkdir(exist_ok=True)
    (vault_dir / "tools").mkdir(exist_ok=True)
    log.append("✓ Структура папок создана")

    config = {
        "version": 1,
        "wallet_name": "ColdVault ETH",
        "chain_id": 1,
        "network": "Ethereum Mainnet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "formatted_by": "ColdVault USB Installer v1.0",
    }
    with open(vault_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    log.append("✓ config.json создан")

    # --- SignOffline.exe ---
    if sign_exe_path and Path(sign_exe_path).is_file():
        shutil.copy2(sign_exe_path, vault_dir / "tools" / "SignOffline.exe")
        shutil.copy2(sign_exe_path, Path(usb_path) / "SignOffline.exe")
        log.append("✓ SignOffline.exe скопирован")
    else:
        log.append("⚠ SignOffline.exe не найден — копируем Python-скрипт")
        _copy_python_fallback(vault_dir)

    # --- autorun.inf ---
    autorun = """[AutoRun]
label=ColdVault ETH
open=launch_signer.bat
action=Запустить ColdVault Signer

[Content]
MusicFiles=false
PictureFiles=false
VideoFiles=false
"""
    (Path(usb_path) / "autorun.inf").write_text(autorun, encoding="utf-8")
    log.append("✓ autorun.inf создан")

    # --- launch_signer.bat ---
    bat = r"""@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH — Офлайн-подпись
color 0A
echo.
echo  ===================================
echo   ColdVault ETH — Офлайн-подпись
echo  ===================================
echo.
if exist "%~dp0SignOffline.exe" (
    start "" "%~dp0SignOffline.exe"
    goto :end
)
if exist "%~dp0ColdVault\tools\SignOffline.exe" (
    start "" "%~dp0ColdVault\tools\SignOffline.exe"
    goto :end
)
echo [!] SignOffline.exe не найден на USB
pause
:end
"""
    (Path(usb_path) / "launch_signer.bat").write_text(bat, encoding="utf-8")
    log.append("✓ launch_signer.bat создан")

    # --- README.txt ---
    readme = """ColdVault ETH — Холодный кошелёк Ethereum
==========================================

ЗАПУСК:
  Windows : дважды кликните launch_signer.bat
  Linux   : ./launch_signer.sh в терминале

СТРУКТУРА:
  ColdVault/
  ├── wallet.vault   — зашифрованный кошелёк
  ├── config.json    — конфигурация
  ├── pending/       — транзакции на подпись
  ├── signed/        — подписанные транзакции
  └── tools/         — утилита подписи

БЕЗОПАСНОСТЬ:
  • Используйте USB ТОЛЬКО на офлайн-компьютере
  • Мнемонику (24 слова) храните на БУМАГЕ
  • Пароль кошелька — единственный способ доступа
"""
    (Path(usb_path) / "README.txt").write_text(readme, encoding="utf-8")
    log.append("✓ README.txt создан")

    return log


def _copy_python_fallback(vault_dir: Path):
    """Копирует Python-скрипты как запасной вариант."""
    if getattr(sys, "frozen", False):
        return
    src_installer = Path(__file__).parent / "sign_offline_exe.py"
    dst = vault_dir / "tools" / "sign_offline.py"
    if src_installer.exists():
        shutil.copy2(src_installer, dst)


# ══════════════════════════════════════════════
#  Worker Thread — выполняет установку в фоне
# ══════════════════════════════════════════════

class InstallerWorker(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, drive: dict, do_format: bool, sign_exe: str = None):
        super().__init__()
        self.drive = drive
        self.do_format = do_format
        self.sign_exe = sign_exe

    def run(self):
        try:
            self._install()
        except Exception as e:
            self.finished_signal.emit(False, str(e))

    def _install(self):
        usb_path = self.drive["path"]
        letter = self.drive.get("letter", usb_path[0])

        # Шаг 1: Форматирование
        if self.do_format:
            self.log_signal.emit(f"[1/3] Форматирование {letter}: в NTFS...")
            self.progress_signal.emit(10)
            ok, msg = format_windows(letter)
            if not ok:
                self.finished_signal.emit(False, msg)
                return
            self.log_signal.emit(f"  ✓ {msg}")
            self.progress_signal.emit(40)
        else:
            self.log_signal.emit("[1/3] Форматирование пропущено")
            self.progress_signal.emit(40)

        # Шаг 2: Установка структуры
        self.log_signal.emit("[2/3] Установка ColdVault...")
        self.progress_signal.emit(50)
        logs = install_coldvault_structure(usb_path, self.sign_exe)
        for line in logs:
            self.log_signal.emit(f"  {line}")
        self.progress_signal.emit(85)

        # Шаг 3: Готово
        self.log_signal.emit("[3/3] Проверка файлов...")
        vault_dir = Path(usb_path) / "ColdVault"
        ok_items = [
            vault_dir.exists(),
            (vault_dir / "config.json").exists(),
            (Path(usb_path) / "README.txt").exists(),
        ]
        self.progress_signal.emit(100)
        if all(ok_items):
            self.finished_signal.emit(True, f"USB готов: {usb_path}")
        else:
            self.finished_signal.emit(False, "Часть файлов не создана, проверьте права доступа")


# ══════════════════════════════════════════════
#  Главное окно
# ══════════════════════════════════════════════

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0d0f0e;
    color: #c8c6c0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}
QLabel#title {
    font-size: 20px;
    font-weight: bold;
    color: #4fc3a0;
    padding: 8px 0;
}
QLabel#subtitle {
    font-size: 12px;
    color: #7a7974;
}
QGroupBox {
    border: 1px solid #2a2d2b;
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px 10px 8px 10px;
    color: #9a9892;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #4fc3a0;
    font-size: 12px;
}
QComboBox {
    background: #1a1d1b;
    border: 1px solid #2e3230;
    border-radius: 5px;
    padding: 6px 10px;
    color: #c8c6c0;
    min-height: 32px;
}
QComboBox:hover { border-color: #4fc3a0; }
QComboBox::drop-down { border: none; padding-right: 10px; }
QComboBox QAbstractItemView {
    background: #1a1d1b;
    border: 1px solid #2e3230;
    selection-background-color: #1f3a30;
    color: #c8c6c0;
}
QPushButton {
    background: #1a1d1b;
    border: 1px solid #2e3230;
    border-radius: 5px;
    padding: 7px 18px;
    color: #c8c6c0;
    min-height: 32px;
}
QPushButton:hover { background: #212723; border-color: #4fc3a0; color: #fff; }
QPushButton:pressed { background: #172019; }
QPushButton:disabled { color: #4a4a48; border-color: #222; }
QPushButton#install_btn {
    background: #1f3a30;
    border-color: #4fc3a0;
    color: #4fc3a0;
    font-weight: bold;
    font-size: 14px;
    min-height: 40px;
}
QPushButton#install_btn:hover { background: #264d3d; color: #6be0b6; }
QPushButton#install_btn:disabled { background: #141e1a; color: #2e5240; border-color: #1e3028; }
QPushButton#warn_btn {
    background: #3a1a1a;
    border-color: #c0392b;
    color: #e74c3c;
    font-weight: bold;
    font-size: 14px;
    min-height: 40px;
}
QPushButton#warn_btn:hover { background: #4d2020; color: #ff6b5b; }
QProgressBar {
    background: #1a1d1b;
    border: 1px solid #2e3230;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #2e7d5a, stop:1 #4fc3a0);
    border-radius: 4px;
}
QTextEdit {
    background: #111412;
    border: 1px solid #1e2320;
    border-radius: 4px;
    padding: 8px;
    color: #7ec8a0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QCheckBox { color: #9a9892; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #3a3e3c;
    border-radius: 3px;
    background: #1a1d1b;
}
QCheckBox::indicator:checked {
    background: #1f3a30;
    border-color: #4fc3a0;
    image: none;
}
QFrame#separator { background: #2a2d2b; max-height: 1px; }
"""


class UsbInstallerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.drives = []
        self._init_ui()
        self._refresh_drives()

    # ─── UI ─── #

    def _init_ui(self):
        self.setWindowTitle("ColdVault — USB Installer")
        self.setMinimumSize(520, 620)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # ── Header ──
        title = QLabel("ColdVault ETH")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Установщик холодного кошелька на USB-флешку")
        sub.setObjectName("subtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addWidget(sub)

        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # ── Выбор диска ──
        disk_group = QGroupBox("Выбор USB-накопителя")
        disk_layout = QHBoxLayout(disk_group)
        self.drive_combo = QComboBox()
        self.drive_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.refresh_btn = QPushButton("↻ Обновить")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self._refresh_drives)
        disk_layout.addWidget(self.drive_combo)
        disk_layout.addWidget(self.refresh_btn)
        root.addWidget(disk_group)

        # ── Параметры ──
        opts_group = QGroupBox("Параметры установки")
        opts_layout = QVBoxLayout(opts_group)

        self.format_check = QCheckBox("Форматировать флешку (NTFS) — ВСЕ ДАННЫЕ БУДУТ УДАЛЕНЫ")
        self.format_check.setChecked(True)
        self.format_check.stateChanged.connect(self._on_format_toggle)
        opts_layout.addWidget(self.format_check)

        self.copy_signer_check = QCheckBox("Копировать SignOffline.exe на флешку")
        self.copy_signer_check.setChecked(True)
        opts_layout.addWidget(self.copy_signer_check)

        root.addWidget(opts_group)

        # ── Предупреждение ──
        self.warn_frame = QGroupBox("⚠  ВНИМАНИЕ")
        warn_layout = QVBoxLayout(self.warn_frame)
        self.warn_label = QLabel(
            "Выбранная флешка будет ОТФОРМАТИРОВАНА.\n"
            "ВСЕ ФАЙЛЫ НА НЕЙ БУДУТ УДАЛЕНЫ безвозвратно.\n"
            "Убедитесь, что выбрана правильная флешка!"
        )
        self.warn_label.setStyleSheet("color: #e74c3c; font-size: 12px;")
        self.warn_label.setWordWrap(True)
        warn_layout.addWidget(self.warn_label)
        root.addWidget(self.warn_frame)

        # ── Прогресс ──
        prog_group = QGroupBox("Прогресс")
        prog_layout = QVBoxLayout(prog_group)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        prog_layout.addWidget(self.progress)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(130)
        prog_layout.addWidget(self.log_view)
        root.addWidget(prog_group)

        # ── Кнопки ──
        btn_layout = QHBoxLayout()
        self.install_btn = QPushButton("⚡  Установить на флешку")
        self.install_btn.setObjectName("warn_btn")
        self.install_btn.clicked.connect(self._on_install_clicked)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.install_btn)
        btn_layout.addWidget(self.cancel_btn)
        root.addWidget(QWidget())  # spacer
        root.addLayout(btn_layout)

        self._log("Готов к работе. Выберите USB-флешку и нажмите 'Установить'.")

    # ─── Логика ─── #

    def _refresh_drives(self):
        self.drives = detect_usb_drives()
        self.drive_combo.clear()
        if self.drives:
            for d in self.drives:
                self.drive_combo.addItem(f"{d['label']}  ({d['path']})  — {d['size']}")
            self._log(f"Найдено USB-накопителей: {len(self.drives)}")
        else:
            self.drive_combo.addItem("— USB-накопители не найдены —")
            self._log("USB не найден. Вставьте флешку и нажмите '↻ Обновить'.")

    def _on_format_toggle(self, state):
        if state:
            self.warn_frame.show()
            self.install_btn.setObjectName("warn_btn")
        else:
            self.warn_frame.hide()
            self.install_btn.setObjectName("install_btn")
        self.install_btn.setStyleSheet(self.styleSheet())

    def _on_install_clicked(self):
        if not self.drives:
            QMessageBox.warning(self, "Ошибка", "USB-накопители не найдены.\nВставьте флешку и обновите список.")
            return

        idx = self.drive_combo.currentIndex()
        if idx < 0 or idx >= len(self.drives):
            return

        drive = self.drives[idx]
        do_format = self.format_check.isChecked()

        # Дополнительное подтверждение при форматировании
        if do_format:
            reply = QMessageBox.warning(
                self,
                "Подтвердите форматирование",
                f"Флешка: {drive['label']} ({drive['path']})\n"
                f"Размер: {drive['size']}\n\n"
                "ВСЕ ДАННЫЕ НА ФЛЕШКЕ БУДУТ УДАЛЕНЫ!\n\n"
                "Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if not is_admin() and platform.system() == "Windows" and do_format:
            QMessageBox.critical(
                self, "Ошибка прав",
                "Форматирование требует прав администратора.\n"
                "Запустите UsbInstaller.exe от имени администратора."
            )
            return

        # Ищем SignOffline.exe
        sign_exe = None
        if self.copy_signer_check.isChecked():
            candidates = [
                BASE_DIR / "SignOffline.exe",
                BASE_DIR / "dist" / "SignOffline.exe",
                Path(sys.executable).parent / "SignOffline.exe",
            ]
            for c in candidates:
                if c.exists():
                    sign_exe = str(c)
                    break
            if not sign_exe:
                self._log("⚠ SignOffline.exe не найден рядом — будет пропущен")

        # Запускаем воркер
        self.install_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_view.clear()
        self._log(f"Начало установки на {drive['path']}...")
        if do_format:
            self._log("  ФОРМАТИРОВАНИЕ включено")

        self.worker = InstallerWorker(drive, do_format, sign_exe)
        self.worker.log_signal.connect(self._log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_finished(self, success: bool, message: str):
        self.install_btn.setEnabled(True)
        self.refresh_btn.setEnabled(True)
        if success:
            self._log(f"\n✅ ГОТОВО! {message}")
            self.progress.setValue(100)
            QMessageBox.information(
                self, "Установка завершена",
                f"Холодный кошелёк установлен на флешку!\n\n{message}\n\n"
                "Безопасно извлеките флешку и используйте её\n"
                "ТОЛЬКО на компьютере БЕЗ интернета."
            )
        else:
            self._log(f"\n❌ ОШИБКА: {message}")
            QMessageBox.critical(
                self, "Ошибка установки",
                f"Установка не завершена:\n\n{message}"
            )

    def _log(self, text: str):
        self.log_view.append(text)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )


# ══════════════════════════════════════════════
#  Точка входа
# ══════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ColdVault USB Installer")
    app.setApplicationVersion("1.0")

    window = UsbInstallerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
