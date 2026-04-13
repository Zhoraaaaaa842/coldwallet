"""
ColdVault ETH - Master Build Script.
"""

import os
import sys
import shutil
import argparse
import subprocess
import time
import threading
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
BUILD_DIR    = PROJECT_ROOT / "build"
DIST_DIR     = PROJECT_ROOT / "dist"
SETUP_DIR    = DIST_DIR / "ColdVault_Setup"
RUST_DIR     = PROJECT_ROOT / "core-rust"
RUST_TARGET  = RUST_DIR / "target" / "wheels"


# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    CYAN   = "\033[96m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    MAGENTA= "\033[95m"
    WHITE  = "\033[97m"
    GRAY   = "\033[90m"


def enable_ansi():
    """Enable ANSI on Windows."""
    if sys.platform == "win32":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
BANNER = r"""

  ░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░ ░▒▓███████▓▒░░▒▓██████▓▒░  
      ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
      ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
      ░▒▓█▓▒░   ░▒▓████████▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓███████▓▒░░▒▓████████▓▒░ 
      ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
      ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
      ░▒▓█▓▒░   ░▒▓█▓▒░░▒▓█▓▒░░▒▓██████▓▒░░▒▓█▓▒░░▒▓█▓▒░▒▓█▓▒░░▒▓█▓▒░ 
"""

SUBTITLE = "  ColdVault ETH  ·  Build System v3  ·  by Zhora"
DIVIDER  = "  " + "─" * 66


def print_banner():
    print(C.CYAN + C.BOLD + BANNER + C.RESET)
    print(C.WHITE + C.BOLD + SUBTITLE + C.RESET)
    print(C.GRAY + DIVIDER + C.RESET)
    print()


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------
BAR_WIDTH = 40

def render_bar(label: str, step: int, total: int, status: str = ""):
    filled = int(BAR_WIDTH * step / total)
    bar    = "█" * filled + "░" * (BAR_WIDTH - filled)
    pct    = int(100 * step / total)
    status_str = f"  {C.GRAY}{status}{C.RESET}" if status else ""
    line = (
        f"  {C.CYAN}{label:<26}{C.RESET} "
        f"{C.BLUE}[{C.CYAN}{bar}{C.BLUE}]{C.RESET} "
        f"{C.WHITE}{pct:>3}%{C.RESET}"
        f"{status_str}"
    )
    print(f"\r{line}", end="", flush=True)


def done_bar(label: str, msg: str = "Done"):
    bar = "█" * BAR_WIDTH
    line = (
        f"  {C.GREEN}{label:<26}{C.RESET} "
        f"{C.GREEN}[{bar}]{C.RESET} "
        f"{C.GREEN}100%  ✓ {msg}{C.RESET}"
    )
    print(f"\r{line}")


def fail_bar(label: str, msg: str = "FAILED"):
    bar = "▓" * BAR_WIDTH
    line = (
        f"  {C.RED}{label:<26}{C.RESET} "
        f"{C.RED}[{bar}]{C.RESET} "
        f"{C.RED} ERR  ✗ {msg}{C.RESET}"
    )
    print(f"\r{line}")


def step_header(index: int, total: int, title: str):
    print()
    print(
        f"  {C.BOLD}{C.YELLOW}[{index}/{total}]{C.RESET} "
        f"{C.WHITE}{C.BOLD}{title}{C.RESET}"
    )
    print(C.GRAY + "  " + "·" * 66 + C.RESET)


def ok(msg: str):
    print(f"  {C.GREEN}✓{C.RESET}  {msg}")


def warn(msg: str):
    print(f"  {C.YELLOW}⚠{C.RESET}  {msg}")


def err(msg: str):
    print(f"  {C.RED}✗{C.RESET}  {C.RED}{msg}{C.RESET}")


# ---------------------------------------------------------------------------
# Spinner для долгих операций
# ---------------------------------------------------------------------------
class Spinner:
    FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

    def __init__(self, label: str):
        self.label   = label
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        i = 0
        while not self._stop.is_set():
            f = self.FRAMES[i % len(self.FRAMES)]
            print(f"\r  {C.CYAN}{f}{C.RESET}  {self.label} ...", end="", flush=True)
            time.sleep(0.08)
            i += 1

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()
        print("\r" + " " * 70 + "\r", end="")


# ---------------------------------------------------------------------------
# Шаг 1: Rust-ядро
# ---------------------------------------------------------------------------

def check_rust_tools() -> bool:
    missing = []
    for tool in ("maturin", "cargo"):
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        err(f"Не найдены: {', '.join(missing)}")
        if "cargo" in missing:
            warn("  Установи Rust: https://rustup.rs")
        if "maturin" in missing:
            warn("  pip install maturin")
        return False
    return True


def build_rust_core() -> Path:
    LABEL = "Rust core (maturin)"
    steps = 8

    render_bar(LABEL, 0, steps, "проверка инструментов")
    if not check_rust_tools():
        fail_bar(LABEL, "maturin/cargo not found")
        sys.exit(1)
    render_bar(LABEL, 1, steps, "очистка старых wheels")

    if RUST_TARGET.exists():
        shutil.rmtree(RUST_TARGET)
    time.sleep(0.1)
    render_bar(LABEL, 2, steps, "запуск cargo build --release")

    proc = subprocess.Popen(
        [sys.executable, "-m", "maturin", "build", "--release",
         "--out", str(RUST_TARGET)],
        cwd=str(RUST_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    cargo_steps = [
        "Compiling", "Finished", "Building", "Linking",
        "Archiving", "Running", "Checking",
    ]
    compiled = set()
    progress = 2
    lines_buf = []

    for line in proc.stdout:
        lines_buf.append(line)
        stripped = line.strip()
        for kw in cargo_steps:
            if kw in stripped and stripped not in compiled:
                compiled.add(stripped)
                progress = min(progress + 1, steps - 1)
                short = stripped[:40].replace("Compiling ", "").replace("Finished ", "")
                render_bar(LABEL, progress, steps, short)
                break

    proc.wait()

    if proc.returncode != 0:
        fail_bar(LABEL)
        print()
        err("maturin завершился с ошибкой:")
        for l in lines_buf[-25:]:
            print(f"    {C.RED}{l.rstrip()}{C.RESET}")
        sys.exit(1)

    wheels = list(RUST_TARGET.glob("coldvault_core-*.whl"))
    if not wheels:
        fail_bar(LABEL, ".whl не найден")
        sys.exit(1)

    done_bar(LABEL, wheels[0].name)
    return wheels[0]


def install_wheel(whl: Path):
    LABEL = "pip install wheel"
    render_bar(LABEL, 0, 3, "подготовка")
    time.sleep(0.1)
    render_bar(LABEL, 1, 3, whl.name)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", str(whl),
         "--force-reinstall", "-q"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail_bar(LABEL)
        err(result.stderr[-400:])
        sys.exit(1)
    render_bar(LABEL, 3, 3)
    done_bar(LABEL, "coldvault_core установлен")


def verify_rust_import():
    LABEL = "Smoke-test import"
    render_bar(LABEL, 0, 2, "from coldvault_core import KeyManager")
    result = subprocess.run(
        [sys.executable, "-c",
         "from coldvault_core import KeyManager; km=KeyManager(); print('OK')"],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or "OK" not in result.stdout:
        fail_bar(LABEL)
        err(result.stderr[-300:])
        sys.exit(1)
    done_bar(LABEL, "KeyManager() OK")


# ---------------------------------------------------------------------------
# Шаг 2: Очистка
# ---------------------------------------------------------------------------

def clean():
    LABEL = "Clean dist/build"
    dirs = [
        DIST_DIR,
        BUILD_DIR / "ZhoraWallet",
        BUILD_DIR / "SignOffline",
        BUILD_DIR / "ZhoraUSB",
    ]
    total = len(dirs)
    for i, d in enumerate(dirs):
        render_bar(LABEL, i, total, str(d.name))
        if d.exists():
            shutil.rmtree(d)
        time.sleep(0.05)
    done_bar(LABEL)


# ---------------------------------------------------------------------------
# Шаг 3: PyInstaller
# ---------------------------------------------------------------------------

def build_exe(spec_name: str, display_name: str) -> bool:
    LABEL = f"PyInstaller {display_name}"
    spec_path = BUILD_DIR / spec_name
    if not spec_path.exists():
        fail_bar(LABEL, f"spec not found: {spec_path}")
        return False

    proc = subprocess.Popen(
        [sys.executable, "-m", "PyInstaller",
         str(spec_path),
         "--distpath", str(DIST_DIR),
         "--workpath", str(BUILD_DIR / display_name.replace(".", "_")),
         "--noconfirm"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    keywords = ["Analyzing","Processing","Building","Appending","Copying","Writing","Completed"]
    seen = set()
    steps = 10
    progress = 0
    lines_buf = []

    for line in proc.stdout:
        lines_buf.append(line)
        stripped = line.strip()
        for kw in keywords:
            if kw in stripped and stripped not in seen:
                seen.add(stripped)
                progress = min(progress + 1, steps - 1)
                short = stripped[:44]
                render_bar(LABEL, progress, steps, short)
                break

    proc.wait()

    if proc.returncode == 0:
        done_bar(LABEL)
        return True
    else:
        fail_bar(LABEL)
        for l in lines_buf[-15:]:
            print(f"    {C.RED}{l.rstrip()}{C.RESET}")
        return False


# ---------------------------------------------------------------------------
# Шаг 4: Пакет
# ---------------------------------------------------------------------------

def create_setup_package():
    LABEL = "Package dist"
    items = [
        "ZhoraWallet.exe", "ZhoraUSB.exe", "SignOffline.exe",
        "whl copy", "scripts", "docs", "INSTALL.bat",
    ]
    total = len(items)
    SETUP_DIR.mkdir(parents=True, exist_ok=True)

    render_bar(LABEL, 0, total, "ZhoraWallet.exe")
    for exe, dest in [
        ("ZhoraWallet.exe", SETUP_DIR / "ZhoraWallet.exe"),
        ("ZhoraUSB.exe",    SETUP_DIR / "ZhoraUSB.exe"),
    ]:
        src = DIST_DIR / exe
        if src.exists():
            shutil.copy2(src, dest)
    render_bar(LABEL, 2, total, "SignOffline.exe")

    usb_dir = SETUP_DIR / "USB_Files"
    usb_dir.mkdir(exist_ok=True)
    signer = DIST_DIR / "SignOffline.exe"
    if signer.exists():
        shutil.copy2(signer, usb_dir / "SignOffline.exe")
    render_bar(LABEL, 3, total, "wheel copy")

    if RUST_TARGET.exists():
        for whl in RUST_TARGET.glob("coldvault_core-*.whl"):
            shutil.copy2(whl, SETUP_DIR / whl.name)
    render_bar(LABEL, 4, total, "scripts")

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
    render_bar(LABEL, 5, total, "docs")

    for doc in ["README.md", "SECURITY_AUDIT.md", "requirements.txt"]:
        src = PROJECT_ROOT / doc
        if src.exists():
            shutil.copy2(src, SETUP_DIR / doc)
    render_bar(LABEL, 6, total, "INSTALL.bat")

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
echo    2. Установить на USB через ZhoraUSB (графический мастер)
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
    done_bar(LABEL)


# ---------------------------------------------------------------------------
# Итог
# ---------------------------------------------------------------------------

def print_summary():
    print()
    print(C.GRAY + DIVIDER + C.RESET)
    print(C.BOLD + C.GREEN + "\n  ✦  СБОРКА ЗАВЕРШЕНА!" + C.RESET)
    print(C.GRAY + DIVIDER + C.RESET)
    print()
    for name, label in [
        ("ZhoraWallet.exe", "десктоп-кошелёк"),
        ("SignOffline.exe",  "USB-подписьщик"),
        ("ZhoraUSB.exe",     "установщик флешки"),
    ]:
        p = DIST_DIR / name
        if p.exists():
            mb = p.stat().st_size / (1024 * 1024)
            print(f"  {C.GREEN}✓{C.RESET}  {C.WHITE}{name:<22}{C.RESET}  {C.CYAN}{mb:>6.1f} MB{C.RESET}  {C.GRAY}({label}){C.RESET}")
        else:
            print(f"  {C.YELLOW}–{C.RESET}  {C.GRAY}{name:<22}  не собран{C.RESET}")
    print()
    print(f"  {C.CYAN}📦 dist/ColdVault_Setup/{C.RESET}")
    print(f"  {C.GRAY}├── ZhoraWallet.exe")
    print(f"  ├── ZhoraUSB.exe")
    print(f"  ├── INSTALL.bat")
    print(f"  ├── coldvault_core-*.whl")
    print(f"  ├── USB_Files/SignOffline.exe")
    print(f"  └── Scripts/{C.RESET}")
    print()
    print(C.GRAY + DIVIDER + C.RESET)
    print(C.BOLD + C.CYAN + "  made by Zhora  ·  ColdVault ETH" + C.RESET)
    print(C.GRAY + DIVIDER + C.RESET)
    print()


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

TOTAL_STEPS = 5

def main():
    enable_ansi()

    parser = argparse.ArgumentParser(description="ColdVault Build System")
    parser.add_argument("--desktop-only",   action="store_true")
    parser.add_argument("--signer-only",    action="store_true")
    parser.add_argument("--installer-only", action="store_true")
    parser.add_argument("--no-clean",       action="store_true")
    parser.add_argument("--skip-rust",      action="store_true")
    args = parser.parse_args()

    print_banner()

    # Проверка PyInstaller
    try:
        import PyInstaller
        ok(f"PyInstaller {PyInstaller.__version__}")
    except ImportError:
        err("PyInstaller не установлен: pip install pyinstaller")
        sys.exit(1)

    # ---- Шаг 1: Rust ----
    step_header(1, TOTAL_STEPS, "Сборка Rust-ядра")
    if args.skip_rust:
        warn("Сборка Rust пропущена (--skip-rust)")
        verify_rust_import()
    else:
        whl = build_rust_core()
        install_wheel(whl)
        verify_rust_import()

    # ---- Шаг 2: Очистка ----
    step_header(2, TOTAL_STEPS, "Очистка предыдущей сборки")
    if not args.no_clean:
        clean()
    else:
        warn("Очистка пропущена (--no-clean)")

    # ---- Шаг 3: PyInstaller ----
    step_header(3, TOTAL_STEPS, "Сборка EXE (PyInstaller)")
    success = True

    if not (args.signer_only or args.installer_only):
        success &= build_exe("coldvault_desktop.spec", "ZhoraWallet")

    if not (args.desktop_only or args.installer_only):
        success &= build_exe("sign_offline.spec", "SignOffline")

    if not (args.desktop_only or args.signer_only):
        success &= build_exe("usb_installer.spec", "ZhoraUSB")

    if not success:
        print()
        err("Сборка завершилась с ошибками.")
        warn("pip install -r requirements.txt && python build_all.py")
        sys.exit(1)

    # ---- Шаг 4: Пакет ----
    step_header(4, TOTAL_STEPS, "Создание дистрибутива")
    create_setup_package()

    # ---- Шаг 5: Итог ----
    step_header(5, TOTAL_STEPS, "Готово")
    print_summary()


if __name__ == "__main__":
    main()
