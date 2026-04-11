@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH - Setup
color 0A
echo.
echo  ========================================
echo    ColdVault ETH - Setup Wizard
echo  ========================================
echo.
echo  Select an option:
echo.
echo    1. Launch ColdVault Desktop (from this folder)
echo    2. Prepare USB drive (format + install)
echo    3. Install wallet to USB (no format)
echo    4. Install USB Watcher (auto-launch on USB connect)
echo    5. Exit
echo.
set /p choice="  Your choice (1-5): "

if "%choice%"=="1" (
    if exist "%~dp0ColdVault.exe" (
        start "" "%~dp0ColdVault.exe"
    ) else (
        echo  [!] ColdVault.exe not found in current folder.
    )
    goto end
)

if "%choice%"=="2" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python not installed. Download: https://python.org
        pause
        goto end
    )
    python "%~dp0Scripts\format_usb.py" --sign-exe "%~dp0USB_Files\SignOffline.exe"
    goto end
)

if "%choice%"=="3" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python not installed.
        pause
        goto end
    )
    python "%~dp0Scripts\install_to_usb.py"
    goto end
)

if "%choice%"=="4" (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [!] Python not installed.
        pause
        goto end
    )
    python "%~dp0Scripts\format_usb.py" --no-format --install-watcher
    goto end
)

:end
echo.
pause
