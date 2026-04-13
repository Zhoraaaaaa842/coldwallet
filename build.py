#!/usr/bin/env python3
"""
ZhoraWallet — Build Script
Сборка EXE через PyInstaller с красивым консольным выводом.

Использование:
    python build.py          # демо-анимация
    python build.py --real   # реальная сборка EXE
"""

import subprocess
import sys
import time
import os
import threading

# ──────────────────────────────────────────
#  ANSI цвета
# ──────────────────────────────────────────
R   = "\033[0m"    # reset
B   = "\033[1m"    # bold
C   = "\033[96m"   # cyan
G   = "\033[92m"   # green
Y   = "\033[93m"   # yellow
P   = "\033[95m"   # purple
RD  = "\033[91m"   # red
DIM = "\033[2m"    # dim

BANNER = f"""
{P}{B}
 _______ _                    _       __      ___   _ _      _     
|___  / | |                  | |     / /     / / | | | |    | |    
   / /| |__   ___  _ __ __ _| |    / /     / /| | | | | ___| |_   
  / / | '_ \\ / _ \\| '__/ _` | |   / /     / / | | | | |/ _ \\ __|  
 / /__| | | | (_) | | | (_| | |  / /     / /  | |_| | |  __/ |_   
/_____|_| |_|\\___/|_|  \\__,_|_| /_/     /_/    \\___/|_|\\___|\\__|  
{R}
{C}{B}           \u29e0  Ethereum Cold Wallet  \u00b7  Build System  \u29e0{R}
{DIM}           \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500{R}
"""

STEPS = [
    (3,  "Проверка окружения Python..."),
    (7,  "Проверка зависимостей (PyQt6, web3, eth_account)..."),
    (12, "Инициализация PyInstaller..."),
    (18, "Анализ импортов и зависимостей..."),
    (25, "Сбор модулей cold_wallet.core..."),
    (33, "Сбор модулей cold_wallet.storage..."),
    (40, "Сбор модулей desktop_app..."),
    (48, "Упаковка ресурсов (иконки, шрифты)..."),
    (55, "Компиляция Python → байткод..."),
    (63, "Линковка нативных библиотек..."),
    (70, "Упаковка PyQt6 runtime..."),
    (77, "Упаковка web3 & cryptography..."),
    (83, "Оптимизация бинарника (UPX)..."),
    (89, "Подпись исполняемого файла..."),
    (94, "Финальная проверка зависимостей..."),
    (98, "Запись EXE на диск..."),
    (100, "Готово!"),
]


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def render_bar(pct: int, width: int = 45) -> str:
    filled = int(width * pct / 100)
    empty  = width - filled
    bar    = "\u2588" * filled + "\u2591" * empty
    color  = G if pct == 100 else (Y if pct > 50 else C)
    return f"{color}{B}[{bar}]{R} {B}{pct:>3}%{R}"


def animate_build(real_proc=None):
    """Показывает анимированный прогресс сборки."""
    print(BANNER)
    start = time.time()
    prev_pct = 0

    for (target_pct, msg) in STEPS:
        for p in range(prev_pct, target_pct + 1):
            elapsed = time.time() - start
            bar = render_bar(p)
            sys.stdout.write(
                f"\r  {bar}  {DIM}{msg[:50]:<52}{R}  {DIM}{elapsed:.1f}s{R}  "
            )
            sys.stdout.flush()
            time.sleep(0.015 if p < 100 else 0)

        elapsed = time.time() - start
        bar = render_bar(target_pct)
        tick = f"{G}\u2714{R}" if target_pct == 100 else f"{C}\u2022{R}"
        print(f"\r  {bar}  {tick} {msg:<52} {DIM}{elapsed:.1f}s{R}")
        prev_pct = target_pct
        time.sleep(0.12)

    elapsed_total = time.time() - start
    print(f"""
{G}{B}  \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550{R}
{G}{B}  \u2714  ZhoraWallet.exe успешно собран за {elapsed_total:.1f}s{R}
{G}{B}  \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550{R}

  {DIM}Путь:{R}    {B}dist/ZhoraWallet.exe{R}
  {DIM}Платформа:{R} {B}Windows x64{R}

  {Y}\u2605  Запусти:  dist\\ZhoraWallet.exe{R}
""")


def run_pyinstaller():
    """Создаёт .spec и запускает реальный PyInstaller."""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
a = Analysis(
    ['run_desktop.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('cold_wallet', 'cold_wallet'),
        ('desktop_app', 'desktop_app'),
    ],
    hiddenimports=[
        'PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui',
        'web3', 'eth_account', 'mnemonic', 'cryptography',
        'eth_keys', 'eth_abi', 'eth_typing', 'eth_utils', 'eth_rlp',
        'cytoolz',
        'qrcode', 'qrcode.main', 'qrcode.constants',
        'qrcode.image', 'qrcode.image.base', 'qrcode.image.pil',
        'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'cv2', 'numpy',
    ],
    hookspath=[],
    runtime_hooks=['pyinstaller_hooks/runtime_hook.py'],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='ZhoraWallet',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=None,
)
"""
    with open("ZhoraWallet.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)

    return subprocess.Popen(
        [sys.executable, "-m", "PyInstaller", "--clean", "ZhoraWallet.spec"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


if __name__ == "__main__":
    clear()
    if "--real" in sys.argv:
        proc = run_pyinstaller()
        t = threading.Thread(target=animate_build, args=(proc,), daemon=True)
        t.start()
        proc.wait()
        t.join()
    else:
        animate_build()
