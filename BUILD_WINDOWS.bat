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
    echo  [!] Python not found. Install Python 3.10+
    echo  [!] https://python.org/downloads
    pause
    exit /b 1
)

echo  [*] Installing dependencies...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Failed to install requirements.txt
    pause
    exit /b 1
)
pip install pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Failed to install PyInstaller
    pause
    exit /b 1
)
echo  [OK] Dependencies installed
echo.

echo  [*] Building ColdVault Desktop (GUI) + SignOffline (Console)...
python build_all.py
if %errorlevel% neq 0 (
    echo  [!] Build failed. Check errors above.
    pause
    exit /b 1
)
echo.

echo  [OK] Done! Files in dist\ColdVault_Setup\
echo.
pause
