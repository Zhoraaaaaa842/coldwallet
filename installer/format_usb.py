"""
ColdVault ETH — Форматирование и подготовка USB-флешки.

ВНИМАНИЕ: Скрипт ФОРМАТИРУЕТ выбранный USB-накопитель!
Все данные на нём будут УДАЛЕНЫ.

Что делает:
1. Обнаруживает USB-накопители
2. Форматирует выбранный в NTFS (Windows) или FAT32 (Linux/macOS)
3. Создаёт структуру ColdVault
4. Копирует SignOffline.exe на USB
5. Создаёт autorun.inf для автозапуска
6. Создаёт launch.bat/.sh для быстрого запуска

Использование:
    python format_usb.py [--sign-exe путь_к_SignOffline.exe]

Требует прав администратора на Windows (для diskpart).
"""

import os
import sys
import json
import shutil
import ctypes
import platform
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cold_wallet.storage.usb_manager import USBManager


# ─── Вспомогательные ─── #

def is_admin() -> bool:
    """Проверяет, запущен ли скрипт от администратора."""
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def confirm_destructive(drive_info: dict) -> bool:
    """Запрос подтверждения перед форматированием."""
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║          ⚠  ВНИМАНИЕ: ФОРМАТИРОВАНИЕ!           ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print(f"  ║  Диск:   {drive_info['label'][:40]:<40} ║")
    print(f"  ║  Путь:   {drive_info['path'][:40]:<40} ║")
    print(f"  ║  Размер: {drive_info['size'][:40]:<40} ║")
    print("  ╠══════════════════════════════════════════════════╣")
    print("  ║  ВСЕ ДАННЫЕ НА ЭТОМ ДИСКЕ БУДУТ УДАЛЕНЫ!        ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    answer = input("  Введите 'ФОРМАТИРОВАТЬ' для подтверждения: ").strip()
    return answer == "ФОРМАТИРОВАТЬ"


# ─── Форматирование ─── #

def format_windows(drive_letter: str, label: str = "COLDVAULT") -> bool:
    """
    Форматирование USB на Windows через format.com.
    Быстрое форматирование в NTFS.
    """
    drive = drive_letter.rstrip("\\").rstrip(":")
    cmd = f'format {drive}: /FS:NTFS /V:{label} /Q /Y'

    print(f"  [*] Форматирование {drive}: в NTFS...")
    print(f"  [*] Команда: {cmd}")

    try:
        # format.com требует ввод — передаём через stdin
        proc = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(input=b"\n", timeout=120)

        if proc.returncode == 0:
            print(f"  [✓] Диск {drive}: отформатирован")
            return True
        else:
            output = (stdout + stderr).decode("cp866", errors="replace")
            print(f"  [!] Ошибка форматирования: {output[:200]}")
            return False
    except subprocess.TimeoutExpired:
        proc.kill()
        print("  [!] Таймаут форматирования")
        return False
    except Exception as e:
        print(f"  [!] Ошибка: {e}")
        return False


def format_linux(device_path: str, mount_point: str, label: str = "COLDVAULT") -> bool:
    """
    Форматирование USB на Linux.
    Использует mkfs.vfat (FAT32) — максимальная совместимость.
    """
    print(f"  [*] Отмонтирование {mount_point}...")
    subprocess.run(["umount", mount_point], capture_output=True)

    # Находим устройство из mount_point
    result = subprocess.run(
        ["findmnt", "-n", "-o", "SOURCE", mount_point],
        capture_output=True, text=True
    )
    device = result.stdout.strip() or device_path

    print(f"  [*] Форматирование {device} в FAT32...")
    proc = subprocess.run(
        ["mkfs.vfat", "-F", "32", "-n", label, device],
        capture_output=True, text=True
    )

    if proc.returncode == 0:
        # Перемонтирование
        subprocess.run(["mount", device, mount_point], capture_output=True)
        print(f"  [✓] Диск отформатирован и смонтирован")
        return True
    else:
        print(f"  [!] Ошибка: {proc.stderr[:200]}")
        return False


# ─── Установка ColdVault на USB ─── #

def install_coldvault_structure(usb_path: str, sign_exe_path: str = None) -> None:
    """Создаёт полную структуру ColdVault на USB."""
    vault_dir = Path(usb_path) / "ColdVault"
    vault_dir.mkdir(exist_ok=True)
    (vault_dir / "pending").mkdir(exist_ok=True)
    (vault_dir / "signed").mkdir(exist_ok=True)
    (vault_dir / "tools").mkdir(exist_ok=True)

    # Config
    config = {
        "version": 1,
        "wallet_name": "ColdVault ETH",
        "chain_id": 1,
        "network": "Ethereum Mainnet",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "formatted_by": "ColdVault USB Formatter v1.0",
    }
    with open(vault_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"  [✓] Структура ColdVault создана")

    # Копируем SignOffline.exe
    if sign_exe_path and os.path.isfile(sign_exe_path):
        dest = vault_dir / "tools" / "SignOffline.exe"
        shutil.copy2(sign_exe_path, dest)
        print(f"  [✓] SignOffline.exe скопирован в tools/")

        # Также копируем в корень USB для удобства
        shutil.copy2(sign_exe_path, Path(usb_path) / "SignOffline.exe")
        print(f"  [✓] SignOffline.exe скопирован в корень USB")
    else:
        # Копируем Python-скрипт как fallback
        script_dir = Path(__file__).parent
        src_files = [
            (script_dir / "sign_offline_exe.py", vault_dir / "tools" / "sign_offline.py"),
        ]
        # Core модули
        core_dest = vault_dir / "tools" / "cold_wallet" / "core"
        core_dest.mkdir(parents=True, exist_ok=True)
        (vault_dir / "tools" / "cold_wallet").joinpath("__init__.py").touch()
        core_dest.joinpath("__init__.py").touch()

        project_root = Path(__file__).parent.parent
        core_files = [
            "cold_wallet/core/key_manager.py",
            "cold_wallet/core/transaction.py",
            "cold_wallet/__init__.py",
        ]
        for cf in core_files:
            src = project_root / cf
            if src.exists():
                dst = vault_dir / "tools" / cf
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

        for src, dst in src_files:
            if src.exists():
                shutil.copy2(src, dst)

        print(f"  [✓] Python-скрипты скопированы (EXE не найден)")


def create_autorun(usb_path: str) -> None:
    """
    Создаёт autorun.inf для Windows.
    
    ПРИМЕЧАНИЕ: Windows 7+ по умолчанию ОТКЛЮЧАЕТ AutoRun для USB.
    autorun.inf задаёт иконку и метку, но НЕ автозапуск.
    Для запуска используется launch.bat.
    """
    autorun_content = """[AutoRun]
label=ColdVault ETH
icon=ColdVault\\tools\\coldvault.ico
open=launch_signer.bat
action=Запустить ColdVault Signer

[Content]
MusicFiles=false
PictureFiles=false
VideoFiles=false
"""
    autorun_path = Path(usb_path) / "autorun.inf"
    with open(autorun_path, "w", encoding="utf-8") as f:
        f.write(autorun_content)
    print(f"  [✓] autorun.inf создан")


def create_launch_scripts(usb_path: str) -> None:
    """Создаёт скрипты быстрого запуска для Windows и Linux."""

    # ─── Windows BAT ─── #
    bat_content = r"""@echo off
chcp 65001 >nul 2>&1
title ColdVault ETH — Офлайн-подпись
color 0A
echo.
echo  ======================================================
echo   ColdVault ETH — Запуск утилиты офлайн-подписи
echo  ======================================================
echo.

:: Проверяем наличие EXE
if exist "%~dp0SignOffline.exe" (
    echo  [*] Запуск SignOffline.exe...
    start "" "%~dp0SignOffline.exe"
    goto :end
)

if exist "%~dp0ColdVault\tools\SignOffline.exe" (
    echo  [*] Запуск ColdVault\tools\SignOffline.exe...
    start "" "%~dp0ColdVault\tools\SignOffline.exe"
    goto :end
)

:: Fallback: Python
echo  [!] SignOffline.exe не найден.
echo  [*] Пробуем запустить через Python...
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python не установлен.
    echo  [!] Скачайте Python: https://python.org
    echo  [!] Или используйте собранный SignOffline.exe
    pause
    goto :end
)

if exist "%~dp0ColdVault\tools\sign_offline.py" (
    python "%~dp0ColdVault\tools\sign_offline.py"
) else (
    echo  [!] Файлы ColdVault не найдены на USB.
)

:end
echo.
pause
"""
    bat_path = Path(usb_path) / "launch_signer.bat"
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"  [✓] launch_signer.bat создан")

    # ─── Linux/macOS Shell ─── #
    sh_content = """#!/bin/bash
# ColdVault ETH — Запуск утилиты офлайн-подписи
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "  ======================================================"
echo "   ColdVault ETH — Запуск утилиты офлайн-подписи"
echo "  ======================================================"
echo ""

# Проверяем Python
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "  [!] Python не установлен."
    echo "  [!] Установите: sudo apt install python3"
    read -p "  Нажмите Enter для выхода..."
    exit 1
fi

if [ -f "$SCRIPT_DIR/ColdVault/tools/sign_offline.py" ]; then
    $PYTHON "$SCRIPT_DIR/ColdVault/tools/sign_offline.py"
else
    echo "  [!] Файлы ColdVault не найдены."
fi

echo ""
read -p "  Нажмите Enter для выхода..."
"""
    sh_path = Path(usb_path) / "launch_signer.sh"
    with open(sh_path, "w", encoding="utf-8") as f:
        f.write(sh_content)
    os.chmod(sh_path, 0o755)
    print(f"  [✓] launch_signer.sh создан")


def create_readme_usb(usb_path: str) -> None:
    """Создаёт README на USB."""
    readme = """╔══════════════════════════════════════════════════════════╗
║                   ColdVault ETH                          ║
║              Холодный кошелёк Ethereum                    ║
╚══════════════════════════════════════════════════════════╝

БЫСТРЫЙ СТАРТ:
═══════════════

Windows:
  1. Дважды кликните "launch_signer.bat"
  2. Или запустите "SignOffline.exe"

Linux/macOS:
  1. Откройте терминал в папке USB
  2. Запустите: ./launch_signer.sh

СТРУКТУРА:
══════════

  ColdVault/
  ├── wallet.vault     — зашифрованный кошелёк
  ├── config.json      — конфигурация
  ├── pending/         — неподписанные транзакции
  ├── signed/          — подписанные транзакции
  └── tools/           — утилита подписи

БЕЗОПАСНОСТЬ:
═════════════

  • Используйте этот USB ТОЛЬКО на офлайн-компьютере
  • НИКОГДА не подключайте к ПК с интернетом при подписи
  • Храните мнемонику (24 слова) ОТДЕЛЬНО на бумаге
  • Пароль кошелька — единственный способ доступа
"""
    with open(Path(usb_path) / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"  [✓] README.txt создан")


# ─── Windows Task Scheduler (автозапуск при вставке USB) ─── #

def create_usb_watcher_task() -> None:
    """
    Создаёт PowerShell-скрипт для мониторинга USB.
    Альтернатива autorun — следит за подключением USB и запускает signer.
    
    Устанавливается в планировщик задач Windows.
    """
    ps_script = r"""
# ColdVault USB Watcher — следит за подключением USB с ColdVault
# Работает как задача в планировщике Windows

$lastDrives = @()

while ($true) {
    $removable = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DriveType -eq 2 }
    $currentDrives = $removable | ForEach-Object { $_.DeviceID }
    
    foreach ($drive in $currentDrives) {
        if ($drive -notin $lastDrives) {
            # Новый USB подключён
            $vaultPath = Join-Path $drive "ColdVault\wallet.vault"
            $signerExe = Join-Path $drive "SignOffline.exe"
            $signerTools = Join-Path $drive "ColdVault\tools\SignOffline.exe"
            
            if (Test-Path $vaultPath) {
                # Нашли ColdVault — проверяем pending TX
                $pendingDir = Join-Path $drive "ColdVault\pending"
                $pendingFiles = @()
                if (Test-Path $pendingDir) {
                    $pendingFiles = Get-ChildItem $pendingDir -Filter "*.json"
                }
                
                if ($pendingFiles.Count -gt 0) {
                    $msg = "ColdVault: Найдено $($pendingFiles.Count) TX для подписи"
                    
                    # Windows Toast уведомление
                    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
                    $template = @"
<toast>
    <visual>
        <binding template="ToastText02">
            <text id="1">ColdVault ETH</text>
            <text id="2">$msg</text>
        </binding>
    </visual>
</toast>
"@
                    try {
                        $xml = [Windows.Data.Xml.Dom.XmlDocument]::new()
                        $xml.LoadXml($template)
                        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ColdVault")
                        $notifier.Show($toast)
                    } catch {
                        # Fallback: MessageBox
                        Add-Type -AssemblyName System.Windows.Forms
                        [System.Windows.Forms.MessageBox]::Show($msg, "ColdVault ETH")
                    }
                    
                    # Запуск signer
                    if (Test-Path $signerExe) {
                        Start-Process $signerExe
                    } elseif (Test-Path $signerTools) {
                        Start-Process $signerTools
                    }
                }
            }
        }
    }
    
    $lastDrives = $currentDrives
    Start-Sleep -Seconds 3
}
"""
    return ps_script


# ─── Главный процесс ─── #

def main():
    parser = argparse.ArgumentParser(description="ColdVault USB Formatter")
    parser.add_argument("--sign-exe", help="Путь к SignOffline.exe", default=None)
    parser.add_argument("--no-format", action="store_true", help="Не форматировать, только установить")
    parser.add_argument("--install-watcher", action="store_true", help="Установить USB watcher (Windows)")
    args = parser.parse_args()

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║    ColdVault ETH — Подготовка USB-флешки             ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    # --- Обнаружение USB ---
    print("  [*] Поиск USB-накопителей...")
    drives = USBManager.detect_usb_drives()

    if not drives:
        print("  [!] USB-накопители не найдены.")
        path = input("  Введите путь вручную (или Enter для выхода): ").strip()
        if not path or not os.path.isdir(path):
            sys.exit(1)
        drives = [{"path": path, "label": os.path.basename(path), "size": "N/A"}]

    print(f"  [✓] Найдено: {len(drives)}")
    for i, d in enumerate(drives, 1):
        existing = " [ColdVault]" if (Path(d["path"]) / "ColdVault").exists() else ""
        print(f"      {i}. {d['label']} ({d['path']}) — {d['size']}{existing}")

    print()
    while True:
        choice = input(f"  Выберите диск (1-{len(drives)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(drives):
                break
        except ValueError:
            pass
        print("  [!] Неверный выбор")

    selected = drives[idx]

    # --- Форматирование ---
    if not args.no_format:
        if not confirm_destructive(selected):
            print("  [*] Отменено.")
            sys.exit(0)

        if platform.system() == "Windows":
            letter = selected["path"].rstrip("\\").rstrip(":")
            if not is_admin():
                print("  [!] Требуются права администратора!")
                print("  [!] Запустите от имени администратора.")
                sys.exit(1)
            if not format_windows(letter):
                print("  [!] Форматирование не удалось.")
                sys.exit(1)
        elif platform.system() == "Linux":
            if not is_admin():
                print("  [!] Требуются права root!")
                print("  [!] Запустите: sudo python format_usb.py")
                sys.exit(1)
            if not format_linux("", selected["path"]):
                print("  [!] Форматирование не удалось.")
                sys.exit(1)
        else:
            print(f"  [!] Автоформатирование не поддерживается на {platform.system()}")
            print("  [*] Отформатируйте USB вручную и запустите с --no-format")
            sys.exit(1)
    else:
        print("  [*] Пропуск форматирования (--no-format)")

    usb_path = selected["path"]

    # --- Установка структуры ---
    print()
    print("  [*] Установка ColdVault на USB...")
    install_coldvault_structure(usb_path, args.sign_exe)
    create_autorun(usb_path)
    create_launch_scripts(usb_path)
    create_readme_usb(usb_path)

    # --- USB Watcher ---
    if args.install_watcher and platform.system() == "Windows":
        ps_script = create_usb_watcher_task()
        watcher_dir = Path(os.environ.get("APPDATA", "")) / "ColdVault"
        watcher_dir.mkdir(exist_ok=True)
        watcher_path = watcher_dir / "usb_watcher.ps1"
        with open(watcher_path, "w", encoding="utf-8") as f:
            f.write(ps_script)

        # Регистрация в планировщике задач
        task_cmd = (
            f'schtasks /Create /TN "ColdVault USB Watcher" '
            f'/TR "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File \\"{watcher_path}\\"" '
            f'/SC ONLOGON /RL HIGHEST /F'
        )
        result = subprocess.run(task_cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  [✓] USB Watcher установлен (автозапуск при входе в систему)")
        else:
            print(f"  [!] Ошибка установки watcher: {result.stderr[:100]}")
            print(f"  [*] Скрипт сохранён: {watcher_path}")
            print(f"  [*] Запустите вручную для мониторинга USB")

    # --- Итог ---
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║           USB ПОДГОТОВЛЕН!                           ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  Диск: {selected['label'][:45]:<45} ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print("  ║  Структура:                                          ║")
    print("  ║    SignOffline.exe        — подпись (Windows)        ║")
    print("  ║    launch_signer.bat      — запуск (Windows)        ║")
    print("  ║    launch_signer.sh       — запуск (Linux/macOS)    ║")
    print("  ║    autorun.inf            — иконка + метка          ║")
    print("  ║    README.txt             — инструкция              ║")
    print("  ║    ColdVault/             — данные кошелька          ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print("  ║  Далее: запустите install_to_usb.py для генерации   ║")
    print("  ║  кошелька, или ColdVault Desktop для работы.        ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
