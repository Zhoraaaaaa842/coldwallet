"""
ColdVault ETH - Master Build Script.

Собирает:
1. ColdVault.exe      - Desktop кошелёк (PyQt6, windowed)
2. SignOffline.exe    - USB офлайн-подписьик (console)
3. UsbInstaller.exe  - GUI-установщик кошелька на флешку (windowed)
4. ColdVault_Setup/   - Итоговый пакет для распространения

Использование:
    python build_all.py [--desktop-only] [--signer-only] [--installer-only] [--clean]
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
SETUP_DIR = DIST_DIR / "ColdVault_Setup"


def clean():
    """Clean previous build artifacts."""
    print("\n  [*] Чистка...")
    for d in [
        DIST_DIR,
        BUILD_DIR / "ColdVault",
        BUILD_DIR / "SignOffline",
        BUILD_DIR / "UsbInstaller",
    ]:
        if d.exists():
            shutil.rmtree(d)
            print(f"      Удалено: {d}")
    for f in PROJECT_ROOT.glob("*.spec"):
        if f.name not in ["coldvault_desktop.spec", "sign_offline.spec", "usb_installer.spec"]:
            f.unlink()
    print("  [OK] Очищено\n")


def build_exe(spec_name: str, display_name: str) -> bool:
    """Build EXE via PyInstaller."""
    spec_path = BUILD_DIR / spec_name
    if not spec_path.exists():
        print(f"  [!] Spec не найден: {spec_path}")
        return False

    print(f"  [*] Сборка {display_name}...")
    print(f"      Spec: {spec_path}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_path),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / display_name.replace(".", "_")),
        "--noconfirm",
    ]

    proc = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )

    if proc.returncode == 0:
        print(f"  [OK] {display_name} собран")
        return True
    else:
        print(f"  [!] Ошибка сборки {display_name}:")
        lines = proc.stderr.strip().split("\n")
        for line in lines[-15:]:
            print(f"      {line}")
        return False


def create_setup_package():
    """Create final distribution package."""
    print("\n  [*] Создание дистрибутива...")

    SETUP_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. ColdVault.exe --- #
    desktop_exe = DIST_DIR / "ColdVault.exe"
    if desktop_exe.exists():
        shutil.copy2(desktop_exe, SETUP_DIR / "ColdVault.exe")
        print("      [OK] ColdVault.exe")

    # --- 2. UsbInstaller.exe --- #
    usb_installer_exe = DIST_DIR / "UsbInstaller.exe"
    if usb_installer_exe.exists():
        shutil.copy2(usb_installer_exe, SETUP_DIR / "UsbInstaller.exe")
        print("      [OK] UsbInstaller.exe")

    # --- 3. USB_Files/SignOffline.exe --- #
    usb_dir = SETUP_DIR / "USB_Files"
    usb_dir.mkdir(exist_ok=True)
    signer_exe = DIST_DIR / "SignOffline.exe"
    if signer_exe.exists():
        shutil.copy2(signer_exe, usb_dir / "SignOffline.exe")
        print("      [OK] SignOffline.exe -> USB_Files/")

    # --- 4. Scripts --- #
    scripts_dir = SETUP_DIR / "Scripts"
    scripts_dir.mkdir(exist_ok=True)

    scripts = [
        "installer/format_usb.py",
        "installer/install_to_usb.py",
        "installer/sign_offline_exe.py",
        "installer/usb_installer_gui.py",
    ]
    for s in scripts:
        src = PROJECT_ROOT / s
        if src.exists():
            shutil.copy2(src, scripts_dir / Path(s).name)
    print("      [OK] Scripts -> Scripts/")

    # --- 5. Core modules --- #
    core_dst = scripts_dir / "cold_wallet" / "core"
    core_dst.mkdir(parents=True, exist_ok=True)
    storage_dst = scripts_dir / "cold_wallet" / "storage"
    storage_dst.mkdir(parents=True, exist_ok=True)

    core_files = [
        "cold_wallet/__init__.py",
        "cold_wallet/core/__init__.py",
        "cold_wallet/core/key_manager.py",
        "cold_wallet/core/transaction.py",
        "cold_wallet/core/eth_network.py",
        "cold_wallet/storage/__init__.py",
        "cold_wallet/storage/usb_manager.py",
    ]
    for cf in core_files:
        src = PROJECT_ROOT / cf
        dst = scripts_dir / cf
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
    print("      [OK] Core modules -> Scripts/cold_wallet/")

    # --- 6. Documentation --- #
    for doc in ["README.md", "SECURITY_AUDIT.md", "requirements.txt"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, SETUP_DIR / doc)
    print("      [OK] Документация")

    # --- 7. INSTALL.bat --- #
    install_bat = r"""@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH - Setup
color 0A
echo.
echo  ========================================
echo    ColdVault ETH - Setup Wizard
echo  ========================================
echo.
echo  Выберите действие:
echo.
echo    1. Запустить ColdVault Desktop
echo    2. Установить на USB (графический мастер) — РЕКОМЕНДУЕТСЯ
echo    3. Установить на USB (командная строка, без форматирования)
echo    4. Выход
echo.
set /p choice="  Ваш выбор (1-4): "

if "%choice%"=="1" (
    if exist "%~dp0ColdVault.exe" (
        start "" "%~dp0ColdVault.exe"
    ) else (
        echo  [!] ColdVault.exe не найден.
    )
    goto end
)

if "%choice%"=="2" (
    if exist "%~dp0UsbInstaller.exe" (
        echo  [*] Запуск графического установщика...
        start "" "%~dp0UsbInstaller.exe"
    ) else (
        echo  [!] UsbInstaller.exe не найден.
    )
    goto end
)

if "%choice%"=="3" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python не установлен.
        pause
        goto end
    )
    python "%~dp0Scripts\install_to_usb.py"
    goto end
)

:end
echo.
pause
"""
    with open(SETUP_DIR / "INSTALL.bat", "w", encoding="utf-8") as f:
        f.write(install_bat)
    print("      [OK] INSTALL.bat")

    print(f"\n  [OK] Дистрибутив готов: {SETUP_DIR}")


def print_summary():
    """Print build summary."""
    print()
    print("  ========================================")
    print("         СБОРКА ЗАВЕРШЕНА!")
    print("  ========================================")

    desktop = DIST_DIR / "ColdVault.exe"
    signer = DIST_DIR / "SignOffline.exe"
    installer = DIST_DIR / "UsbInstaller.exe"

    if desktop.exists():
        size_mb = desktop.stat().st_size / (1024 * 1024)
        print(f"  ColdVault.exe      - {size_mb:>6.1f} MB  (десктоп)")
    else:
        print("  ColdVault.exe      - НЕ СОБРАН")

    if signer.exists():
        size_mb = signer.stat().st_size / (1024 * 1024)
        print(f"  SignOffline.exe    - {size_mb:>6.1f} MB  (USB-подписьик)")
    else:
        print("  SignOffline.exe    - НЕ СОБРАН")

    if installer.exists():
        size_mb = installer.stat().st_size / (1024 * 1024)
        print(f"  UsbInstaller.exe  - {size_mb:>6.1f} MB  (установщик флешки)")
    else:
        print("  UsbInstaller.exe  - НЕ СОБРАН")

    print()
    print("  Дистрибутив: dist/ColdVault_Setup/")
    print("  ----------------------------------------")
    print("  dist/ColdVault_Setup/")
    print("  |-- ColdVault.exe       - десктоп-приложение")
    print("  |-- UsbInstaller.exe    - установка на флешку (GUI)")
    print("  |-- INSTALL.bat         - мастер установки")
    print("  |-- USB_Files/")
    print("  |   +-- SignOffline.exe  - для флешки")
    print("  |-- Scripts/            - Python-скрипты")
    print("  |-- README.md")
    print("  +-- SECURITY_AUDIT.md")
    print("  ========================================")
    print()


def main():
    parser = argparse.ArgumentParser(description="ColdVault Build System")
    parser.add_argument("--desktop-only", action="store_true")
    parser.add_argument("--signer-only", action="store_true")
    parser.add_argument("--installer-only", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    print()
    print("  ========================================")
    print("    ColdVault ETH - Build System v2")
    print("  ========================================")

    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  [!] PyInstaller не установлен: pip install pyinstaller")
        sys.exit(1)

    if not args.no_clean:
        clean()

    success = True

    # --- ColdVault.exe ---
    if not args.signer_only and not args.installer_only:
        if not build_exe("coldvault_desktop.spec", "ColdVault"):
            success = False

    # --- SignOffline.exe ---
    if not args.desktop_only and not args.installer_only:
        if not build_exe("sign_offline.spec", "SignOffline"):
            success = False

    # --- UsbInstaller.exe ---
    if not args.desktop_only and not args.signer_only:
        if not build_exe("usb_installer.spec", "UsbInstaller"):
            success = False

    if success:
        create_setup_package()
        print_summary()
    else:
        print("\n  [!] Сборка завершена с ошибками.")
        print("  [*] Проверьте зависимости: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
