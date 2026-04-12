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
    echo [!] Python не найден. Установи Python 3.10+
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
    echo [!] Rust не найден. Установи через rustup:
    echo [!] https://rustup.rs
    echo.
    echo     Открыть страницу загрузки? (Y/N)
    set /p openrust="> "
    if /i "%openrust%"=="Y" start https://rustup.rs
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('cargo --version') do echo [OK] %%v

:: -------------------------------------------------------
:: 3. Python-зависимости
:: -------------------------------------------------------
echo.
echo [*] Установка Python-зависимостей...
python -m pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [!] Ошибка установки requirements.txt
    pause
    exit /b 1
)

python -m pip install maturin pyinstaller qrcode[pil] Pillow opencv-python -q
if %errorlevel% neq 0 (
    echo [!] Ошибка установки maturin/pyinstaller
    pause
    exit /b 1
)
echo [OK] Зависимости установлены

:: -------------------------------------------------------
:: 4. Сборка (Rust -> whl -> PyInstaller)
:: -------------------------------------------------------
echo.
echo [*] Запуск build_all.py...
echo.

python build_all.py %*
if %errorlevel% neq 0 (
    echo.
    echo [!] Сборка завершилась с ошибками. Проверь вывод выше.
    pause
    exit /b 1
)

echo.
echo  ========================================
echo    Готово! dist\ColdVault_Setup\
echo  ========================================
echo.
pause
