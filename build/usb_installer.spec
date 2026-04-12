# -*- mode: python ; coding: utf-8 -*-
# ColdVault ETH — USB Installer spec
# Собирается в: dist/ZhoraUSB.exe

from pathlib import Path

BLOCK_CIPHER = None
ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'installer' / 'usb_installer_gui.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
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
    name='ZhoraUSB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='build/coldvault.ico',
    uac_admin=True,
)
