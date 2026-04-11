"""
ColdVault ETH — Установщик на USB.
Запускается на офлайн-ПК для инициализации холодного кошелька на флешке.

Использование:
    python install_to_usb.py

Шаги:
1. Обнаруживает USB-накопители
2. Создаёт структуру ColdVault
3. Генерирует или импортирует кошелёк
4. Шифрует и сохраняет на USB
5. Копирует утилиту подписи (sign_offline.py) на USB
"""

import os
import sys
import shutil
import getpass
from pathlib import Path

# Добавляем родительскую директорию в PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cold_wallet.core.key_manager import KeyManager
from cold_wallet.storage.usb_manager import USBManager


def print_header():
    print("\n" + "=" * 60)
    print("   ColdVault ETH — Установка холодного кошелька на USB")
    print("=" * 60)
    print()


def select_usb() -> str:
    """Выбор USB-накопителя."""
    print("[*] Поиск USB-накопителей...")
    drives = USBManager.detect_usb_drives()

    if not drives:
        print("\n[!] USB-накопители не обнаружены.")
        print("    Вставьте флешку и попробуйте снова.")
        manual = input("\n    Или введите путь вручную (Enter для выхода): ").strip()
        if manual and os.path.isdir(manual):
            return manual
        sys.exit(1)

    print(f"\n[*] Обнаружено USB-накопителей: {len(drives)}\n")
    for i, drive in enumerate(drives, 1):
        status = ""
        vault_path = Path(drive["path"]) / "ColdVault"
        if vault_path.exists():
            status = " [ColdVault установлен]"
        print(f"    {i}. {drive['label']} ({drive['path']}) — {drive['size']}{status}")

    print()
    while True:
        choice = input(f"    Выберите номер (1-{len(drives)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(drives):
                return drives[idx]["path"]
        except ValueError:
            pass
        print("    [!] Некорректный выбор, попробуйте снова")


def get_secure_password() -> str:
    """Запрос пароля с подтверждением."""
    print("\n[*] Установите пароль для шифрования кошелька.")
    print("    Требования: минимум 8 символов.")
    print("    ЗАПОМНИТЕ ЭТОТ ПАРОЛЬ — восстановление невозможно!\n")

    while True:
        password = getpass.getpass("    Пароль: ")
        if len(password) < 8:
            print("    [!] Пароль слишком короткий (мин. 8 символов)")
            continue

        confirm = getpass.getpass("    Подтверждение: ")
        if password != confirm:
            print("    [!] Пароли не совпадают, попробуйте снова")
            continue

        return password


def setup_wallet(km: KeyManager) -> None:
    """Генерация или импорт кошелька."""
    print("\n[*] Выберите действие:")
    print("    1. Создать новый кошелёк (рекомендуется)")
    print("    2. Импортировать из мнемоники (24 слова)")
    print("    3. Импортировать из приватного ключа")
    print()

    choice = input("    Выбор (1/2/3): ").strip()

    if choice == "1":
        mnemonic, address = km.generate_wallet()
        print("\n" + "=" * 60)
        print("   МНЕМОНИЧЕСКАЯ ФРАЗА — ЗАПИШИТЕ НА БУМАГЕ!")
        print("=" * 60)
        print()
        words = mnemonic.split()
        for i in range(0, len(words), 4):
            line = "   ".join(f"{i+j+1:2d}. {words[i+j]}" for j in range(min(4, len(words)-i)))
            print(f"    {line}")
        print()
        print("=" * 60)
        print("   НЕ ФОТОГРАФИРУЙТЕ! НЕ СОХРАНЯЙТЕ В ФАЙЛ!")
        print("   Это единственный способ восстановить кошелёк.")
        print("=" * 60)
        print(f"\n    Адрес: {address}")

        input("\n    Нажмите Enter после того, как запишете фразу...")

        # Верификация: просим ввести несколько слов
        import random
        check_indices = sorted(random.sample(range(len(words)), 3))
        print("\n[*] Проверка: введите слова по номерам:")
        for idx in check_indices:
            while True:
                word = input(f"    Слово #{idx+1}: ").strip().lower()
                if word == words[idx]:
                    break
                print("    [!] Неверно, попробуйте снова")
        print("\n    [✓] Мнемоника подтверждена!")

    elif choice == "2":
        print("\n    Введите 24 слова через пробел:")
        mnemonic = input("    > ").strip()
        try:
            address = km.import_from_mnemonic(mnemonic)
            print(f"\n    [✓] Кошелёк импортирован: {address}")
        except ValueError as e:
            print(f"\n    [!] Ошибка: {e}")
            sys.exit(1)

    elif choice == "3":
        print("\n    Введите приватный ключ (hex):")
        pk = input("    > ").strip()
        try:
            address = km.import_from_private_key(pk)
            print(f"\n    [✓] Кошелёк импортирован: {address}")
        except ValueError as e:
            print(f"\n    [!] Ошибка: {e}")
            sys.exit(1)
    else:
        print("    [!] Некорректный выбор")
        sys.exit(1)


def copy_signing_tool(vault_path: Path) -> None:
    """Копирует утилиту подписи на USB."""
    src_dir = Path(__file__).parent.parent
    dest_dir = vault_path / "tools"
    dest_dir.mkdir(exist_ok=True)

    # Копируем необходимые модули
    files_to_copy = [
        ("cold_wallet/core/key_manager.py", "core/key_manager.py"),
        ("cold_wallet/core/transaction.py", "core/transaction.py"),
        ("cold_wallet/core/__init__.py", "core/__init__.py"),
        ("cold_wallet/__init__.py", "__init__.py"),
        ("installer/sign_offline.py", "sign_offline.py"),
    ]

    for src_rel, dst_rel in files_to_copy:
        src = src_dir / src_rel
        dst = dest_dir / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            shutil.copy2(src, dst)

    print(f"    [✓] Утилита подписи скопирована на USB")


def main():
    print_header()

    # 1. Выбор USB
    usb_path = select_usb()
    print(f"\n    [✓] Выбран: {usb_path}")

    # 2. Инициализация структуры
    usb = USBManager(usb_path)
    usb.initialize_usb()
    print(f"    [✓] Структура ColdVault создана")

    # 3. Генерация/импорт кошелька
    km = KeyManager()
    setup_wallet(km)

    # 4. Шифрование и сохранение
    password = get_secure_password()
    wallet_path = str(usb.wallet_file)
    km.encrypt_and_save(password, wallet_path)
    print(f"\n    [✓] Кошелёк зашифрован и сохранён на USB")

    # 5. Копирование утилиты подписи
    copy_signing_tool(usb.vault_path)

    # 6. Очистка ключей из памяти
    km.clear()

    print("\n" + "=" * 60)
    print("   УСТАНОВКА ЗАВЕРШЕНА!")
    print("=" * 60)
    print(f"""
    Структура на USB:
    {usb_path}/ColdVault/
    ├── wallet.vault        — зашифрованный кошелёк
    ├── config.json         — конфигурация
    ├── pending/            — входящие TX для подписи
    ├── signed/             — подписанные TX
    └── tools/              — утилита офлайн-подписи

    Следующие шаги:
    1. Безопасно извлеките USB
    2. Установите десктоп-приложение ColdVault на онлайн-ПК
    3. Подключайте USB только для подписи транзакций
    """)


if __name__ == "__main__":
    main()
