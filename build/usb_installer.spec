# -*- mode: python ; coding: utf-8 -*-
# ColdVault ETH — USB Installer spec
# Собирается в: dist/UsbInstaller.exe

from PyInstaller.utils.hooks import collect_all
from pathlib import Path
import sys

BLOCK_CIPHER = None
ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'installer' / 'usb_installer_gui.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Иконки/шрифты если есть
    ],
    hiddenimports=[
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.sip',
        'cold_wallet',
        'cold_wallet.storage',
        'cold_wallet.storage.usb_manager',
        'ctypes',
        'wmi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'web3',
        'eth_account',
        'cryptography',
        'tkinter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=BLOCK_CIPHER,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=BLOCK_CIPHER)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='UsbInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # GUI-приложение (без консоли)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='build/coldvault.ico',   # раскомментируй если есть иконка
    uac_admin=True,        # Windows: запрос прав администратора
)
