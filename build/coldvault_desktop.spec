# -*- mode: python ; coding: utf-8 -*-
"""
ColdVault Desktop — PyInstaller spec.
Сборка: pyinstaller build/coldvault_desktop.spec
Результат: dist/ZhoraWallet.exe
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPECPATH)))
if not os.path.isfile(os.path.join(PROJECT_ROOT, 'run_desktop.py')):
    PROJECT_ROOT = os.path.dirname(os.path.abspath(SPECPATH))
    if not os.path.isfile(os.path.join(PROJECT_ROOT, 'run_desktop.py')):
        PROJECT_ROOT = os.getcwd()

block_cipher = None

a = Analysis(
    [os.path.join(PROJECT_ROOT, 'run_desktop.py')],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=[
        (os.path.join(PROJECT_ROOT, 'cold_wallet'), 'cold_wallet'),
        (os.path.join(PROJECT_ROOT, 'desktop_app'), 'desktop_app'),
    ],
    hiddenimports=[
        'eth_account',
        'eth_account._utils',
        'eth_account._utils.signing',
        'eth_account._utils.legacy_transactions',
        'eth_account.typed_transactions',
        'eth_account.typed_transactions.typed_transaction',
        'eth_account.typed_transactions.dynamic_fee_transaction',
        'eth_account.signers',
        'eth_account.signers.local',
        'eth_account.messages',
        'eth_keys',
        'eth_keys.backends',
        'eth_keys.backends.native',
        'eth_abi',
        'eth_abi.codec',
        'eth_typing',
        'eth_utils',
        'eth_utils.decorators',
        'eth_rlp',
        'eth_hash',
        'eth_hash.auto',
        'hexbytes',
        'rlp',
        'cytoolz',
        'toolz',
        'web3',
        'web3.auto',
        'web3.eth',
        'web3.middleware',
        'web3.providers',
        'web3.providers.rpc',
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.ciphers',
        'cryptography.hazmat.primitives.ciphers.aead',
        'cryptography.hazmat.primitives.kdf',
        'cryptography.hazmat.primitives.kdf.pbkdf2',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.backends',
        'mnemonic',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.sip',
        'json',
        'decimal',
        'pathlib',
        'typing',
        'dataclasses',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZhoraWallet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/coldvault.ico',
)
