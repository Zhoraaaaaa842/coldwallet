@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH - Build EXE
color 0A

echo.
echo  ========================================
echo    ColdVault ETH - Automated EXE Build
echo  ========================================
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found. Install Python 3.10+
    echo [!] https://python.org/downloads
    pause
    exit /b 1
)

echo [*] Installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [!] Failed to install requirements.txt
    pause
    exit /b 1
)

echo [*] Installing QR + build tools...
pip install qrcode[pil] Pillow opencv-python pyinstaller
if %errorlevel% neq 0 (
    echo [!] Failed to install QR/build dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed
echo.

echo [*] Cleaning old build cache...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist ColdVault.spec del /q ColdVault.spec

echo [*] Building ColdVault.exe...
python build_exe.py
if %errorlevel% neq 0 (
    echo [!] Build failed. Check errors above.
    pause
    exit /b 1
)

echo.
echo [OK] Done! File: dist\ColdVault.exe
echo.
pause
