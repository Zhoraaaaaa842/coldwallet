"""
ColdVault ETH - Master Build Script.

Порядок сборки:
  1. Rust-ядро  → maturin build --release  → coldvault_core-*.whl
  2. Установка .whl в текущий venv
  3. ZhoraWallet.exe   → PyInstaller (windowed)
  4. SignOffline.exe   → PyInstaller (console)
  5. ZhoraUSB.exe      → PyInstaller (windowed)
  6. ColdVault_Setup/  → итоговый пакет

Использование:
    python build_all.py [--desktop-only] [--signer-only] [--installer-only] [--no-clean] [--skip-rust]
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
BUILD_DIR    = PROJECT_ROOT / "build"
DIST_DIR     = PROJECT_ROOT / "dist"
SETUP_DIR    = DIST_DIR / "ColdVault_Setup"
RUST_DIR     = PROJECT_ROOT / "core-rust"
RUST_TARGET  = RUST_DIR / "target" / "wheels"


# ---------------------------------------------------------------------------
# Шаг 1: Сборка Rust-ядра
# ---------------------------------------------------------------------------

def check_rust_tools() -> bool:
    """Returns False if maturin or cargo not found."""
    missing = []
    for tool in ("maturin", "cargo"):
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        print(f"  [!] Не найдены: {', '.join(missing)}")
        print("      Установка:")
        if "cargo" in missing:
            print("        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh")
        if "maturin" in missing:
            print("        pip install maturin")
        return False
    return True


def build_rust_core() -> Path:
    """
    Собирает Rust-ядро через maturin build --release.
    Возвращает путь к .whl файлу.
    """
    print("\n  [*] Сборка Rust-ядра (maturin build --release)...")

    if not check_rust_tools():
        sys.exit(1)

    # Старая .whl удаляем, чтобы не установить устаревшую версию
    if RUST_TARGET.exists():
        shutil.rmtree(RUST_TARGET)

    result = subprocess.run(
        [
            sys.executable, "-m", "maturin",
            "build", "--release",
            "--out", str(RUST_TARGET),
        ],
        cwd=str(RUST_DIR),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("  [!] maturin завершился с ошибкой:")
        for line in result.stderr.strip().splitlines()[-20:]:
            print(f"      {line}")
        sys.exit(1)

    wheels = list(RUST_TARGET.glob("coldvault_core-*.whl"))
    if not wheels:
        print("  [!] .whl файл не найден после сборки")
        sys.exit(1)

    whl = wheels[0]
    print(f"  [OK] Собран: {whl.name}")
    return whl


def install_wheel(whl: Path):
    """pip install --force-reinstall <whl> в текущий venv."""
    print(f"  [*] Установка {whl.name}...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", str(whl), "--force-reinstall", "-q"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("  [!] pip install не удался:")
        print(result.stderr[-500:])
        sys.exit(1)
    print("  [OK] coldvault_core установлен в venv")


def verify_rust_import():
    """Quick smoke-test: проверяем что модуль импортируется."""
    result = subprocess.run(
        [sys.executable, "-c",
         "from coldvault_core import KeyManager; km=KeyManager(); print('OK')"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or "OK" not in result.stdout:
        print("  [!] Импорт coldvault_core не удался:")
        print(result.stderr[-300:])
        sys.exit(1)
    print("  [OK] coldvault_core импорт прошёл")


# ---------------------------------------------------------------------------
# Шаг 2: Очистка / сборка EXE
# ---------------------------------------------------------------------------

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
    print("  [OK] Очищено\n")


def find_pyd(package: str) -> Path | None:
    """
    Находит .pyd / .so файл coldvault_core в site-packages.
    PyInstaller добавляет его автоматически, но путь полезен для spec.
    """
    import importlib.util
    spec = importlib.util.find_spec(package)
    if spec and spec.origin:
        return Path(spec.origin)
    return None


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
        for line in proc.stderr.strip().splitlines()[-15:]:
            print(f"      {line}")
        return False


# ---------------------------------------------------------------------------
# Шаг 3: Пакетирование
# ---------------------------------------------------------------------------

def create_setup_package():
    print("\n  [*] Создание дистрибутива...")
    SETUP_DIR.mkdir(parents=True, exist_ok=True)

    # EXE-файлы
    for exe, dest in [
        ("ZhoraWallet.exe", SETUP_DIR / "ZhoraWallet.exe"),
        ("ZhoraUSB.exe",    SETUP_DIR / "ZhoraUSB.exe"),
    ]:
        src = DIST_DIR / exe
        if src.exists():
            shutil.copy2(src, dest)
            print(f"      [OK] {exe}")

    usb_dir = SETUP_DIR / "USB_Files"
    usb_dir.mkdir(exist_ok=True)
    signer = DIST_DIR / "SignOffline.exe"
    if signer.exists():
        shutil.copy2(signer, usb_dir / "SignOffline.exe")
        print("      [OK] SignOffline.exe -> USB_Files/")

    # Копируем .whl для документации / dev-установки без сборки
    if RUST_TARGET.exists():
        for whl in RUST_TARGET.glob("coldvault_core-*.whl"):
            shutil.copy2(whl, SETUP_DIR / whl.name)
            print(f"      [OK] {whl.name}")

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
    print("      [OK] Scripts/")

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
    print("      [OK] cold_wallet/ модули")

    for doc in ["README.md", "SECURITY_AUDIT.md", "requirements.txt"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, SETUP_DIR / doc)
    print("      [OK] Документация")

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
echo    3. Установить на USB (командная строка)
echo    4. Выход
echo.
set /p choice="  Ваш выбор (1-4): "
if "%choice%"=="1" ( start "" "%~dp0ZhoraWallet.exe" & goto end )
if "%choice%"=="2" ( start "" "%~dp0ZhoraUSB.exe" & goto end )
if "%choice%"=="3" ( python "%~dp0Scripts\install_to_usb.py" & goto end )
:end
pause
"""
    with open(SETUP_DIR / "INSTALL.bat", "w", encoding="utf-8") as f:
        f.write(install_bat)
    print("      [OK] INSTALL.bat")
    print(f"\n  [OK] Дистрибутив: {SETUP_DIR}")


# ---------------------------------------------------------------------------
# Отчёт
# ---------------------------------------------------------------------------

def print_summary():
    print()
    print("  ========================================")
    print("         СБОРКА ЗАВЕРШЕНА!")
    print("  ========================================")
    for name, label in [
        ("ZhoraWallet.exe", "десктоп-кошелёк"),
        ("SignOffline.exe",  "USB-подписьщик"),
        ("ZhoraUSB.exe",     "установщик флешки"),
    ]:
        p = DIST_DIR / name
        if p.exists():
            mb = p.stat().st_size / (1024 * 1024)
            print(f"  {name:<20} {mb:>6.1f} MB  ({label})")
        else:
            print(f"  {name:<20} НЕ СОБРАН")
    print()
    print("  dist/ColdVault_Setup/")
    print("  ├── ZhoraWallet.exe")
    print("  ├── ZhoraUSB.exe")
    print("  ├── INSTALL.bat")
    print("  ├── coldvault_core-*.whl   ← Rust-ядро")
    print("  ├── USB_Files/SignOffline.exe")
    print("  └── Scripts/")
    print("  ========================================")


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="ColdVault Build System")
    parser.add_argument("--desktop-only",   action="store_true", help="Только ZhoraWallet.exe")
    parser.add_argument("--signer-only",    action="store_true", help="Только SignOffline.exe")
    parser.add_argument("--installer-only", action="store_true", help="Только ZhoraUSB.exe")
    parser.add_argument("--no-clean",       action="store_true", help="Не удалять предыдущую сборку")
    parser.add_argument("--skip-rust",      action="store_true", help="Пропустить сборку Rust (если .whl уже установлен)")
    args = parser.parse_args()

    print()
    print("  ========================================")
    print("    ColdVault ETH - Build System v3")
    print("  ========================================")

    # Проверка PyInstaller
    try:
        import PyInstaller
        print(f"  [OK] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("  [!] PyInstaller не установлен: pip install pyinstaller")
        sys.exit(1)

    # --- Шаг 1: Rust ---
    if args.skip_rust:
        print("  [~] Сборка Rust пропущена (--skip-rust)")
        verify_rust_import()  # всё равно проверяем что модуль есть
    else:
        whl = build_rust_core()
        install_wheel(whl)
        verify_rust_import()

    # --- Шаг 2: Чистка ---
    if not args.no_clean:
        clean()

    # --- Шаг 3: PyInstaller ---
    success = True

    if not (args.signer_only or args.installer_only):
        success &= build_exe("coldvault_desktop.spec", "ZhoraWallet")

    if not (args.desktop_only or args.installer_only):
        success &= build_exe("sign_offline.spec", "SignOffline")

    if not (args.desktop_only or args.signer_only):
        success &= build_exe("usb_installer.spec", "ZhoraUSB")

    # --- Шаг 4: Пакет ---
    if success:
        create_setup_package()
        print_summary()
    else:
        print("\n  [!] Сборка завершилась с ошибками.")
        print("  [*] Проверьте зависимости: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
