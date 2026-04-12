#!/usr/bin/env python3
"""
ZhoraWallet ETH — Скрипт сборки EXE.

Использование:
    python build_exe.py

Результат:
    dist/ZhoraWallet.exe
"""

import subprocess
import sys
import os
import time
import threading

# ────────────────────── ANSI ──────────────────────
R   = "\033[0m"
B   = "\033[1m"
C   = "\033[96m"
G   = "\033[92m"
Y   = "\033[93m"
P   = "\033[95m"
DIM = "\033[2m"

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
    bar    = "█" * filled + "░" * (width - filled)
    color  = G if pct == 100 else (Y if pct > 50 else C)
    return f"{color}{B}[{bar}]{R} {B}{pct:>3}%{R}"


def animate(proc: subprocess.Popen):
    """Анимация прогресса пока работает PyInstaller."""
    print(BANNER)
    start = time.time()
    prev  = 0

    for (target, msg) in STEPS:
        # ждём — либо анимируем плавно, либо пока процесс не завершился
        for p in range(prev, target + 1):
            if proc.poll() is not None and p < target:
                break
            elapsed = time.time() - start
            sys.stdout.write(
                f"\r  {render_bar(p)}  {DIM}{msg[:50]:<52}{R}  {DIM}{elapsed:.1f}s{R}  "
            )
            sys.stdout.flush()
            time.sleep(0.015)

        elapsed = time.time() - start
        tick = f"{G}✔{R}" if target == 100 else f"{C}•{R}"
        print(f"\r  {render_bar(target)}  {tick} {msg:<52} {DIM}{elapsed:.1f}s{R}")
        prev = target
        time.sleep(0.12)

        if proc.poll() is not None and target < 100:
            # PyInstaller завершился раньше анимации — догоняем
            continue

    total = time.time() - start
    print(f"""
{G}{B}  ══════════════════════════════════════════════════════════{R}
{G}{B}  ✔  ZhoraWallet.exe успешно собран за {total:.1f}s{R}
{G}{B}  ══════════════════════════════════════════════════════════{R}

  {DIM}Путь:{R}      {B}dist/ZhoraWallet.exe{R}
  {DIM}Платформа:{R}  {B}Windows x64{R}

  {Y}★  Запусти:  dist\\ZhoraWallet.exe{R}
""")


def build():
    clear()
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ZhoraWallet",
        "--onefile",
        "--windowed",
        # "--icon=assets/icon.ico",
        "--add-data", f"cold_wallet{os.pathsep}cold_wallet",
        "--add-data", f"desktop_app{os.pathsep}desktop_app",
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
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=qrcode",
        "--hidden-import=qrcode.image",
        "--hidden-import=qrcode.image.pil",
        "--hidden-import=qrcode.image.base",
        "--hidden-import=qrcode.constants",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=PIL.ImageFont",
        "--collect-all=qrcode",
        "--collect-all=PIL",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--hidden-import=numpy.core",
        "--hidden-import=numpy.core._methods",
        "--hidden-import=numpy.lib.format",
        "--collect-all=cv2",
        "--collect-all=eth_account",
        "--collect-all=web3",
        "run_desktop.py",
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Анимация в основном потоке, PyInstaller в фоне
    t = threading.Thread(target=animate, args=(proc,), daemon=True)
    t.start()
    proc.wait()
    t.join()

    if proc.returncode != 0:
        print(f"\n{chr(27)}[91m[!] Ошибка сборки. Запусти с --log для деталей.{chr(27)}[0m")
        sys.exit(1)


if __name__ == "__main__":
    build()
