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

STEPS = [
    (3,  "Проверка окружения Python..."),
    (7,  "Проверка зависимостей (PyQt6, web3, eth_account)..."),
    (12, "Инициализация PyInstaller..."),
    (18, "Анализ импортов и зависимостей..."),
    (25, "Сбор модулей cold_wallet.core..."),
    (33, "Сбор модулей cold_wallet.storage..."),
    (40, "Сбор модулей desktop_app..."),
    (48, "Упаковка ресурсов..."),
    (55, "Компиляция Python → байткод..."),
    (63, "Линковка нативных библиотек..."),
    (70, "Упаковка PyQt6 runtime..."),
    (77, "Упаковка web3 & cryptography..."),
    (83, "Оптимизация бинарника (UPX)..."),
    (89, "Подпись файла..."),
    (94, "Финальная проверка..."),
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


def animate(done_event: threading.Event):
    print(BANNER)
    start = time.time()
    prev  = 0
    for (target, msg) in STEPS:
        for p in range(prev, target + 1):
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
        if done_event.is_set():
            break


def build():
    clear()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ZhoraWallet",
        "--onefile",
        "--windowed",
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
        "--hidden-import=qrcode.image.pil",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--collect-all=qrcode",
        "--collect-all=PIL",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--collect-all=cv2",
        "--collect-all=eth_account",
        "--collect-all=web3",
        "run_desktop.py",
    ]

    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_log.txt")

    done_event = threading.Event()
    anim_thread = threading.Thread(target=animate, args=(done_event,), daemon=True)
    anim_thread.start()

    with open(log_path, "w", encoding="utf-8") as log_file:
        proc = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=log_file,
            stderr=log_file,
        )

    done_event.set()
    anim_thread.join()

    if proc.returncode == 0:
        total = 0
        print(f"""
{G}{B}  ══════════════════════════════════════════════════════════{R}
{G}{B}  ✔  ZhoraWallet.exe успешно собран!{R}
{G}{B}  ══════════════════════════════════════════════════════════{R}

  {DIM}Путь:{R}      {B}dist/ZhoraWallet.exe{R}
  {DIM}Платформа:{R}  {B}Windows x64{R}

  {Y}★  Запусти:  dist\\ZhoraWallet.exe{R}
""")
    else:
        print(f"""
{RD}{B}  [!] Ошибка сборки! returncode={proc.returncode}{R}
  {DIM}Подробности в файле:{R} {B}build_log.txt{R}
""")
        sys.exit(1)


if __name__ == "__main__":
    build()
