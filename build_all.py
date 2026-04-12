"""
ColdVault ETH - Master Build Script.

Собирает:
1. ZhoraWallet.exe   - Desktop кошелёк (PyQt6, windowed)
2. SignOffline.exe   - USB офлайн-подписьик (console)
3. ZhoraUSB.exe      - GUI-установщик кошелька на флешку (windowed)
4. ColdVault_Setup/  - Итоговый пакет для распространения

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
    print("\n  [*] Чистка...")
    for d in [
        DIST_DIR,
        BUILD_DIR / "ZhoraWallet",
        BUILD_DIR / "SignOffline",
        BUILD_DIR / "ZhoraUSB",
    ]:
        if d.exists():
            shutil.rmtree(d)
            print(f"      Удалено: {d}")
    for f in PROJECT_ROOT.glob("*.spec"):
        if f.name not in ["coldvault_desktop.spec", "sign_offline.spec", "usb_installer.spec"]:
            f.unlink()
    print("  [OK] Очищено\n")


def build_exe(spec_name: str, display_name: str) -> bool:
    spec_path = BUILD_DIR / spec_name
    if not spec_path.exists():
        print(f"  [!] Spec не найден: {spec_path}")
        return False

    print(f"  [*] Сборка {display_name}...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(spec_path),
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR / display_name.replace(".", "_")),
        "--noconfirm",
    ]

    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)

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
    print("\n  [*] Создание дистрибутива...")
    SETUP_DIR.mkdir(parents=True, exist_ok=True)

    # --- ZhoraWallet.exe ---
    wallet_exe = DIST_DIR / "ZhoraWallet.exe"
    if wallet_exe.exists():
        shutil.copy2(wallet_exe, SETUP_DIR / "ZhoraWallet.exe")
        print("      [OK] ZhoraWallet.exe")

    # --- ZhoraUSB.exe ---
    usb_exe = DIST_DIR / "ZhoraUSB.exe"
    if usb_exe.exists():
        shutil.copy2(usb_exe, SETUP_DIR / "ZhoraUSB.exe")
        print("      [OK] ZhoraUSB.exe")

    # --- USB_Files/SignOffline.exe ---
    usb_dir = SETUP_DIR / "USB_Files"
    usb_dir.mkdir(exist_ok=True)
    signer_exe = DIST_DIR / "SignOffline.exe"
    if signer_exe.exists():
        shutil.copy2(signer_exe, usb_dir / "SignOffline.exe")
        print("      [OK] SignOffline.exe -> USB_Files/")

    # --- Scripts ---
    scripts_dir = SETUP_DIR / "Scripts"
    scripts_dir.mkdir(exist_ok=True)
    for s in [
        "installer/format_usb.py",
        "installer/install_to_usb.py",
        "installer/sign_offline_exe.py",
        "installer/usb_installer_gui.py",
    ]:
        src = PROJECT_ROOT / s
        if src.exists():
            shutil.copy2(src, scripts_dir / Path(s).name)
    print("      [OK] Scripts -> Scripts/")

    # --- Core modules ---
    for cf in [
        "cold_wallet/__init__.py",
        "cold_wallet/core/__init__.py",
        "cold_wallet/core/key_manager.py",
        "cold_wallet/core/transaction.py",
        "cold_wallet/core/eth_network.py",
        "cold_wallet/storage/__init__.py",
        "cold_wallet/storage/usb_manager.py",
    ]:
        src = PROJECT_ROOT / cf
        dst = scripts_dir / cf
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)
    print("      [OK] Core modules -> Scripts/cold_wallet/")

    # --- Docs ---
    for doc in ["README.md", "SECURITY_AUDIT.md", "requirements.txt"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, SETUP_DIR / doc)
    print("      [OK] Документация")

    # --- INSTALL.bat ---
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
echo    1. Запустить ZhoraWallet (десктоп-кошелёк)
echo    2. Установить на USB через ZhoraUSB (графический мастер) — РЕКОМЕНДУЕТСЯ
echo    3. Установить на USB (без форматирования, командная строка)
echo    4. Выход
echo.
set /p choice="  Ваш выбор (1-4): "

if "%choice%"=="1" (
    if exist "%~dp0ZhoraWallet.exe" (
        start "" "%~dp0ZhoraWallet.exe"
    ) else (
        echo  [!] ZhoraWallet.exe не найден.
    )
    goto end
)

if "%choice%"=="2" (
    if exist "%~dp0ZhoraUSB.exe" (
        echo  [*] Запуск установщика...
        start "" "%~dp0ZhoraUSB.exe"
    ) else (
        echo  [!] ZhoraUSB.exe не найден.
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
    print()
    print("  ========================================")
    print("         СБОРКА ЗАВЕРШЕНА!")
    print("  ========================================")

    for exe_name, label in [
        ("ZhoraWallet.exe", "десктоп-кошелёк"),
        ("SignOffline.exe",  "USB-подписьик"),
        ("ZhoraUSB.exe",     "установщик флешки"),
    ]:
        p = DIST_DIR / exe_name
        if p.exists():
            mb = p.stat().st_size / (1024 * 1024)
            print(f"  {exe_name:<20} - {mb:>6.1f} MB  ({label})")
        else:
            print(f"  {exe_name:<20} - НЕ СОБРАН")

    print()
    print("  Дистрибутив: dist/ColdVault_Setup/")
    print("  ----------------------------------------")
    print("  dist/ColdVault_Setup/")
    print("  |-- ZhoraWallet.exe     - десктоп-приложение")
    print("  |-- ZhoraUSB.exe        - установка на флешку (GUI)")
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

    if not args.signer_only and not args.installer_only:
        if not build_exe("coldvault_desktop.spec", "ZhoraWallet"):
            success = False

    if not args.desktop_only and not args.installer_only:
        if not build_exe("sign_offline.spec", "SignOffline"):
            success = False

    if not args.desktop_only and not args.signer_only:
        if not build_exe("usb_installer.spec", "ZhoraUSB"):
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
