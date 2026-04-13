#!/usr/bin/env python3
"""
ZhoraWallet ETH — Сборка EXE с реальным прогрессом.

Использование:
    python build_exe.py

Результат:
    dist/ZhoraWallet.exe
"""

import subprocess
import sys
import os
import time
import shutil

R   = "\033[0m"
B   = "\033[1m"
C   = "\033[96m"
G   = "\033[92m"
Y   = "\033[93m"
P   = "\033[95m"
DIM = "\033[2m"
RD  = "\033[91m"

BANNER = f"""
{P}{B}
 _______ _                    _       __      ___   _ _      _
|___  / | |                  | |     / /     / / | | | |    | |
   / /| |__   ___  _ __ __ _| |    / /     / /| | | | | ___| |_
  / / | '_ \\ / _ \\| '__/ _` | |   / /     / / | | | | |/ _ \\ __|
 / /__| | | | (_) | | | (_| | |  / /     / /  | |_| | |  __/ |_
/_____|_| |_|\\___/|_|  \\__,_|_| /_/     /_/    \\___/|_|\\___|\\__|
{R}
{C}{B}           ⧠  Ethereum Cold Wallet  ·  Build System  ⧠{R}
{DIM}           ─────────────────────────────────────────────{R}
"""


def find_python_with_deps():
    """Автоматически ищет Python с установленными PIL и qrcode через PATH и sys.executable."""
    candidates = []

    # Поиск через PATH
    for name in ["python", "python3", "py"]:
        found = shutil.which(name)
        if found and found not in candidates:
            candidates.append(found)

    # Текущий Python как запасной вариант
    if sys.executable not in candidates:
        candidates.append(sys.executable)

    for py in candidates:
        if not os.path.isfile(py):
            continue
        try:
            result = subprocess.run(
                [py, "-c", "import PIL; import qrcode; import qrcode.image.pil; print('ok')"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "ok" in result.stdout:
                return py
        except Exception:
            continue
    return None


# Ключевые фразы из вывода PyInstaller → (процент, описание)
PROGRESS_MAP = [
    ("run Analysis",             3,  "Анализ импортов..."),
    ("Analyzing",                8,  "Анализ зависимостей..."),
    ("Collecting submodules",    15, "Сбор субмодулей..."),
    ("Collecting data files",    22, "Сбор дата-файлов..."),
    ("Processing pre-find",      28, "Предобработка модулей..."),
    ("Looking for ctypes",       33, "Поиск ctypes-зависимостей..."),
    ("Processing post-find",     38, "Постобработка модулей..."),
    ("Building PKG",             45, "Сборка PKG-архива..."),
    ("Bootloader",               52, "Добавление bootloader..."),
    ("Warnings",                 57, "Проверка предупреждений..."),
    ("Building EXE",             65, "Сборка EXE-файла..."),
    ("Appending PKG archive",    75, "Упаковка PKG в EXE..."),
    ("Fixing EXE headers",       82, "Исправление заголовков EXE..."),
    ("Copying icons",            87, "Установка иконки..."),
    ("Building EXE from",        92, "Финализация EXE..."),
    ("successfully built",       98, "Запись на диск..."),
]


def render_bar(pct: int, width: int = 45) -> str:
    filled = int(width * pct / 100)
    bar    = "█" * filled + "░" * (width - filled)
    color  = G if pct == 100 else (Y if pct > 50 else C)
    return f"{color}{B}[{bar}]{R} {B}{pct:>3}%{R}"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def build():
    clear()
    print(BANNER)

    # ── Проверяем Python с зависимостями ──
    python_exe = find_python_with_deps()
    if python_exe is None:
        print(f"{RD}{B}  [!] Не найден Python с установленными PIL и qrcode!{R}")
        print(f"  Установите зависимости командой:")
        print(f"  {Y}pip install qrcode[pil] Pillow{R}")
        sys.exit(1)

    print(f"  {G}✔{R} Используется Python: {B}{python_exe}{R}\n")

    # Путь к runtime hook (принудительный импорт PIL/qrcode)
    hook_dir = os.path.dirname(os.path.abspath(__file__))
    runtime_hook = os.path.join(hook_dir, "pyinstaller_hooks", "runtime_hook.py")

    cmd = [
        python_exe, "-m", "PyInstaller",
        "--name=ZhoraWallet",
        "--onefile",
        "--windowed",
        "--add-data", f"cold_wallet{os.pathsep}cold_wallet",
        "--add-data", f"desktop_app{os.pathsep}desktop_app",
        # Runtime hook — гарантирует загрузку PIL и qrcode в бандле
        f"--runtime-hook={runtime_hook}",
        # Ethereum
        "--hidden-import=eth_account",
        "--hidden-import=web3",
        "--hidden-import=mnemonic",
        "--hidden-import=cryptography",
        "--hidden-import=eth_keys",
        "--hidden-import=eth_abi",
        "--hidden-import=eth_typing",
        "--hidden-import=eth_utils",
        "--hidden-import=eth_rlp",
        "--hidden-import=cytoolz",
        # GUI
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        # QR + Pillow — все субмодули явно + сбор бинарных .dll/.pyd
        "--hidden-import=qrcode",
        "--hidden-import=qrcode.main",
        "--hidden-import=qrcode.constants",
        "--hidden-import=qrcode.image",
        "--hidden-import=qrcode.image.base",
        "--hidden-import=qrcode.image.pil",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=PIL.ImageFont",
        "--hidden-import=PIL.ImageOps",
        "--hidden-import=PIL.ImageFilter",
        "--collect-submodules=qrcode",
        "--collect-all=PIL",       # FIX: собирает .pyd/.dll + данные Pillow
        "--collect-all=qrcode",    # FIX: был только collect-submodules, добавляем data
        # OpenCV
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--collect-all=cv2",
        "--collect-all=eth_account",
        "--collect-all=web3",
        "run_desktop.py",
    ]

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_log.txt")
    cwd      = os.path.dirname(os.path.abspath(__file__))

    proc = subprocess.Popen(
        cmd, cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        bufsize=1,
    )

    pct       = 0
    start     = time.time()
    log_lines = []

    for raw_line in proc.stdout:
        line = raw_line.strip()
        log_lines.append(line)

        for keyword, target_pct, label in PROGRESS_MAP:
            if keyword.lower() in line.lower() and target_pct > pct:
                for p in range(pct + 1, target_pct + 1):
                    elapsed = time.time() - start
                    sys.stdout.write(
                        f"\r  {render_bar(p)}  {DIM}{label[:52]:<54}{R}  {DIM}{elapsed:.1f}s{R}  "
                    )
                    sys.stdout.flush()
                    time.sleep(0.02)
                elapsed = time.time() - start
                print(f"\r  {render_bar(target_pct)}  {C}•{R} {label:<54} {DIM}{elapsed:.1f}s{R}")
                pct = target_pct
                break

    proc.wait()

    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))

    if proc.returncode == 0:
        for p in range(pct + 1, 101):
            elapsed = time.time() - start
            sys.stdout.write(
                f"\r  {render_bar(p)}  {DIM}Готово!{R}  {DIM}{elapsed:.1f}s{R}  "
            )
            sys.stdout.flush()
            time.sleep(0.015)
        elapsed = time.time() - start
        print(f"\r  {render_bar(100)}  {G}✔{R} Готово!{' ' * 50} {DIM}{elapsed:.1f}s{R}")
        print(f"""
{G}{B}  ══════════════════════════════════════════════════════════{R}
{G}{B}  ✔  ZhoraWallet.exe успешно собран за {elapsed:.1f}s{R}
{G}{B}  ══════════════════════════════════════════════════════════{R}

  {DIM}Путь:{R}      {B}dist/ZhoraWallet.exe{R}
  {DIM}Платформа:{R}  {B}Windows x64{R}

  {Y}★  Запусти:  dist\\ZhoraWallet.exe{R}
""")
    else:
        elapsed = time.time() - start
        print(f"""
{RD}{B}  [!] Ошибка сборки! (returncode={proc.returncode}, {elapsed:.1f}s){R}
  {DIM}Подробности:{R} {B}build_log.txt{R}
""")
        tail = log_lines[-20:] if len(log_lines) >= 20 else log_lines
        print(f"{RD}── Последние строки лога ──{R}")
        for l in tail:
            print(f"  {DIM}{l}{R}")
        sys.exit(1)


if __name__ == "__main__":
    build()
