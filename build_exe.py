#!/usr/bin/env python3
"""
ZhoraWallet ETH — Скрипт сборки EXE через PyInstaller.

Использование:
    python build_exe.py          # демо-анимация прогресса
    python build_exe.py --real   # реальная сборка EXE

Результат:
    dist/ZhoraWallet.exe
"""

# Делегируем в основной build.py
import runpy, sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
runpy.run_path(os.path.join(os.path.dirname(__file__), 'build.py'), run_name='__main__')
