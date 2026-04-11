"""
ColdVault ETH - Master Build Script.

Builds:
1. ColdVault.exe      - Desktop app (PyQt6, windowed)
2. SignOffline.exe     - USB offline signer (console)
3. ColdVault_Setup/    - Final distribution package

Usage:
    python build_all.py [--desktop-only] [--signer-only] [--clean]
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
    print("\n  [*] Cleaning...")
    for d in [DIST_DIR, BUILD_DIR / "ColdVault", BUILD_DIR / "SignOffline"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"      Removed: {d}")
    # Remove stray .spec artifacts in project root
    for f in PROJECT_ROOT.glob("*.spec"):
        if f.name not in ["coldvault_desktop.spec", "sign_offline.spec"]:
            f.unlink()
    print("  [OK] Cleaned\n")


def build_exe(spec_name: str, display_name: str) -> bool:
    """Build EXE via PyInstaller."""
    spec_path = BUILD_DIR / spec_name
    if not spec_path.exists():
        print(f"  [!] Spec file not found: {spec_path}")
        return False

    print(f"  [*] Building {display_name}...")
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
        print(f"  [OK] {display_name} built successfully")
        return True
    else:
        print(f"  [!] Build error for {display_name}:")
        # Show last 15 lines of stderr
        lines = proc.stderr.strip().split("\n")
        for line in lines[-15:]:
            print(f"      {line}")
        return False


def create_setup_package():
    """Create final distribution package."""
    print("\n  [*] Creating distribution package...")

    SETUP_DIR.mkdir(parents=True, exist_ok=True)

    # --- Desktop EXE --- #
    desktop_exe = DIST_DIR / "ColdVault.exe"
    if desktop_exe.exists():
        shutil.copy2(desktop_exe, SETUP_DIR / "ColdVault.exe")
        print("      [OK] ColdVault.exe")

    # --- USB directory --- #
    usb_dir = SETUP_DIR / "USB_Files"
    usb_dir.mkdir(exist_ok=True)

    signer_exe = DIST_DIR / "SignOffline.exe"
    if signer_exe.exists():
        shutil.copy2(signer_exe, usb_dir / "SignOffline.exe")
        print("      [OK] SignOffline.exe -> USB_Files/")

    # --- Install scripts --- #
    scripts_dir = SETUP_DIR / "Scripts"
    scripts_dir.mkdir(exist_ok=True)

    scripts = [
        "installer/format_usb.py",
        "installer/install_to_usb.py",
        "installer/sign_offline_exe.py",
    ]
    for s in scripts:
        src = PROJECT_ROOT / s
        if src.exists():
            shutil.copy2(src, scripts_dir / src.name)
    print("      [OK] Scripts -> Scripts/")

    # --- Core modules (Python fallback) --- #
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

    # --- Documentation --- #
    for doc in ["README.md", "SECURITY_AUDIT.md", "requirements.txt"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, SETUP_DIR / doc)
    print("      [OK] Documentation")

    # --- Windows quick-install BAT --- #
    install_bat = r"""@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH - Setup
color 0A
echo.
echo  ========================================
echo    ColdVault ETH - Setup Wizard
echo  ========================================
echo.
echo  Select an option:
echo.
echo    1. Launch ColdVault Desktop (from this folder)
echo    2. Prepare USB drive (format + install)
echo    3. Install wallet to USB (no format)
echo    4. Install USB Watcher (auto-launch on USB connect)
echo    5. Exit
echo.
set /p choice="  Your choice (1-5): "

if "%choice%"=="1" (
    if exist "%~dp0ColdVault.exe" (
        start "" "%~dp0ColdVault.exe"
    ) else (
        echo  [!] ColdVault.exe not found in current folder.
    )
    goto end
)

if "%choice%"=="2" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python not installed. Download: https://python.org
        pause
        goto end
    )
    python "%~dp0Scripts\format_usb.py" --sign-exe "%~dp0USB_Files\SignOffline.exe"
    goto end
)

if "%choice%"=="3" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python not installed.
        pause
        goto end
    )
    python "%~dp0Scripts\install_to_usb.py"
    goto end
)

if "%choice%"=="4" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python not installed.
        pause
        goto end
    )
    python "%~dp0Scripts\format_usb.py" --no-format --install-watcher
    goto end
)

:end
echo.
pause
"""
    with open(SETUP_DIR / "INSTALL.bat", "w", encoding="utf-8") as f:
        f.write(install_bat)
    print("      [OK] INSTALL.bat")

    print(f"\n  [OK] Distribution ready: {SETUP_DIR}")


def print_summary():
    """Print build summary."""
    print()
    print("  ========================================")
    print("         BUILD COMPLETE!")
    print("  ========================================")

    desktop = DIST_DIR / "ColdVault.exe"
    signer = DIST_DIR / "SignOffline.exe"

    if desktop.exists():
        size_mb = desktop.stat().st_size / (1024 * 1024)
        print(f"  ColdVault.exe    - {size_mb:>6.1f} MB  (desktop)")
    else:
        print("  ColdVault.exe    - NOT BUILT")

    if signer.exists():
        size_mb = signer.stat().st_size / (1024 * 1024)
        print(f"  SignOffline.exe   - {size_mb:>6.1f} MB  (USB signer)")
    else:
        print("  SignOffline.exe   - NOT BUILT")

    print()
    print("  Distribution: dist/ColdVault_Setup/")
    print("  ----------------------------------------")
    print("  dist/ColdVault_Setup/")
    print("  |-- ColdVault.exe      - desktop app")
    print("  |-- INSTALL.bat        - setup wizard")
    print("  |-- USB_Files/")
    print("  |   +-- SignOffline.exe - for USB drive")
    print("  |-- Scripts/           - Python scripts")
    print("  |-- README.md")
    print("  +-- SECURITY_AUDIT.md")
    print("  ========================================")
    print()


def main():
    parser = argparse.ArgumentParser(description="ColdVault Build System")
    parser.add_argument("--desktop-only", action="store_true")
    parser.add_argument("--signer-only", action="store_true")
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    print()
    print("  ========================================")
    print("    ColdVault ETH - Build System")
    print("  ========================================")

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  [!] PyInstaller not installed: pip install pyinstaller")
        sys.exit(1)

    if not args.no_clean:
        clean()

    success = True

    if not args.signer_only:
        if not build_exe("coldvault_desktop.spec", "ColdVault"):
            success = False

    if not args.desktop_only:
        if not build_exe("sign_offline.spec", "SignOffline"):
            success = False

    if success:
        create_setup_package()
        print_summary()
    else:
        print("\n  [!] Build finished with errors.")
        print("  [*] Check dependencies: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
