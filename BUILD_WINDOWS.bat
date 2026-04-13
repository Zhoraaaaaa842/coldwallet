@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH - Build EXE
color 0A

echo.
echo  ========================================
echo    ColdVault ETH - Automated EXE Build
echo  ========================================
echo.

:: -------------------------------------------------------
:: 1. Python
:: -------------------------------------------------------
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python not found. Install Python 3.10+
    echo [!] https://python.org/downloads
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v

:: -------------------------------------------------------
:: 2. Rust + Cargo
:: -------------------------------------------------------
where cargo >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Rust not found. Install via rustup:
    echo [!] https://rustup.rs
    echo.
    echo     Open download page? (Y/N)
    set /p openrust="> "
    if /i "%openrust%"=="Y" start https://rustup.rs
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('cargo --version') do echo [OK] %%v

:: -------------------------------------------------------
:: 3. Python dependencies
:: -------------------------------------------------------
echo.
echo [*] Installing Python dependencies...
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [!] Error installing requirements.txt
    pause
    exit /b 1
)

python -m pip install maturin pyinstaller qrcode[pil] Pillow opencv-python -q
if %errorlevel% neq 0 (
    echo [!] Error installing maturin/pyinstaller
    pause
    exit /b 1
)
echo [OK] Dependencies installed

:: -------------------------------------------------------
:: 4. Build (Rust -> whl -> PyInstaller)
:: -------------------------------------------------------
echo.
echo [*] Running build_all.py...
echo.

python build_all.py %*
if %errorlevel% neq 0 (
    echo.
    echo [!] Build failed. Check output above.
    pause
    exit /b 1
)

echo.
echo  ========================================
echo    Done! dist\ColdVault_Setup\
echo  ========================================
echo.
pause
