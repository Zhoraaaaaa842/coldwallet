"""
ColdVault ETH — Скрипт сборки EXE через PyInstaller.

Использование:
    python build_exe.py

Результат:
    dist/ColdVault.exe
"""

import subprocess
import sys
import os


def build_desktop_app():
    print("[*] Сборка ColdVault Desktop...")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=ColdVault",
        "--onefile",
        "--windowed",
        # "--icon=assets/icon.ico",
        "--add-data", f"cold_wallet{os.pathsep}cold_wallet",
        "--add-data", f"desktop_app{os.pathsep}desktop_app",

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

        # PyQt6
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",

        # QR-коды: qrcode + Pillow
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

        # OpenCV (декодирование QR)
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

    result = subprocess.run(cmd, cwd=os.path.dirname(os.path.abspath(__file__)))

    if result.returncode == 0:
        print("\n[✓] Сборка завершена!")
        print("    Файл: dist/ColdVault.exe")
    else:
        print("\n[!] Ошибка сборки")
        sys.exit(1)


if __name__ == "__main__":
    build_desktop_app()
