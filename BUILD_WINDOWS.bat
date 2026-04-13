@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH - Build
color 0A

:: Add Rust to PATH
set "PATH=C:\Users\%USERNAME%\.cargo\bin;%PATH%"

:: Python check
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python not found. Install Python 3.10+
    echo  [!] https://python.org/downloads
    pause
    exit /b 1
)

:: Cargo check
cargo --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Rust not found. Install via https://rustup.rs
    pause
    exit /b 1
)

:: Install deps silently
python -m pip install -r requirements.txt -q
python -m pip install maturin pyinstaller qrcode[pil] Pillow opencv-python -q

:: Launch beautiful build UI
python build_all.py %*

if %errorlevel% neq 0 (
    echo.
    pause
    exit /b 1
)
pause
