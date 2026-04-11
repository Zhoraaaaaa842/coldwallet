"""
ColdVault ETH — Утилита офлайн-подписи (EXE-версия).
Запускается С USB-ФЛЕШКИ на офлайн-ПК.

Алгоритм поиска vault:
1. Папка, откуда запущен EXE → ищет wallet.vault рядом
2. Родитель EXE-папки (если EXE в tools/)
3. Все буквы дисков A:-Z: → ищет ColdVault/wallet.vault
"""

import os
import sys
import json
import getpass
import string
import platform
from pathlib import Path
from typing import Optional

# --- Определяем базовый путь (PyInstaller vs обычный запуск) ---
if getattr(sys, 'frozen', False):
    # Запущен как EXE
    EXE_DIR = Path(sys.executable).parent
else:
    EXE_DIR = Path(__file__).parent

# Добавляем пути для импорта
sys.path.insert(0, str(EXE_DIR))
sys.path.insert(0, str(EXE_DIR.parent))

from cold_wallet.core.key_manager import KeyManager
from cold_wallet.core.transaction import TransactionSigner, TransactionRequest


def find_vault_root() -> Optional[Path]:
    """
    Ищет папку ColdVault с wallet.vault.
    Приоритет:
    1. Рядом с EXE (EXE лежит прямо в ColdVault/)
    2. Родитель EXE (EXE в ColdVault/tools/)
    3. Сканирование removable drives (Windows: A:-Z:, Linux: /media/*)
    """
    # 1. Рядом с EXE
    if (EXE_DIR / "wallet.vault").exists():
        return EXE_DIR

    # 2. Родитель (EXE в tools/)
    parent = EXE_DIR.parent
    if (parent / "wallet.vault").exists():
        return parent

    # 3. Ищем ColdVault/ на всех дисках
    if platform.system() == "Windows":
        for letter in string.ascii_uppercase:
            vault = Path(f"{letter}:\\ColdVault")
            if vault.exists() and (vault / "wallet.vault").exists():
                return vault
    else:
        # Linux/macOS: /media, /mnt, /run/media
        for base in ["/media", "/mnt", "/run/media"]:
            base_path = Path(base)
            if base_path.exists():
                for mount in base_path.rglob("ColdVault"):
                    if mount.is_dir() and (mount / "wallet.vault").exists():
                        return mount

    return None


def print_header():
    os.system("cls" if platform.system() == "Windows" else "clear")
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                                                      ║")
    print("  ║       ◈  ColdVault ETH — Офлайн-подпись             ║")
    print("  ║                                                      ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    print("  ⚠  Убедитесь, что этот ПК ОТКЛЮЧЁН от интернета!")
    print("  " + "─" * 54)
    print()


def display_tx_details(tx_data: dict) -> None:
    """Показывает детали транзакции перед подписью."""
    tx = tx_data.get("tx", {})

    value_wei = int(tx.get("value_wei", 0))
    value_eth = value_wei / 1e18

    print("  ┌─────────────────────────────────────────────────┐")
    print(f"  │  Получатель:  {tx.get('to', 'N/A')[:42]}")
    print(f"  │  Сумма:       {value_eth:.8f} ETH")
    print(f"  │  Nonce:       {tx.get('nonce', 'N/A')}")
    print(f"  │  Chain ID:    {tx.get('chain_id', 'N/A')}")
    print(f"  │  Gas Limit:   {tx.get('gas_limit', 'N/A')}")

    if tx.get("tx_type") == "eip1559":
        max_fee = int(tx.get("max_fee_per_gas", 0)) / 1e9
        priority = int(tx.get("max_priority_fee_per_gas", 0)) / 1e9
        print(f"  │  Тип:         EIP-1559")
        print(f"  │  Max Fee:     {max_fee:.4f} Gwei")
        print(f"  │  Priority:    {priority:.4f} Gwei")
    else:
        gas_price = int(tx.get("gas_price", 0)) / 1e9
        print(f"  │  Тип:         Legacy")
        print(f"  │  Gas Price:   {gas_price:.4f} Gwei")

    # Макс. стоимость
    if tx.get("tx_type") == "eip1559":
        max_cost = value_wei + int(tx.get("gas_limit", 21000)) * int(tx.get("max_fee_per_gas", 0))
    else:
        max_cost = value_wei + int(tx.get("gas_limit", 21000)) * int(tx.get("gas_price", 0))
    print(f"  │  Макс. цена:  {max_cost / 1e18:.8f} ETH")
    print("  └─────────────────────────────────────────────────┘")
    print()


def main():
    print_header()

    # --- Поиск vault ---
    print("  [*] Поиск ColdVault на подключённых дисках...")
    vault_root = find_vault_root()

    if vault_root is None:
        print("  [!] ColdVault не найден.")
        print("  [!] Убедитесь, что USB-флешка подключена и содержит")
        print("      папку ColdVault/ с файлом wallet.vault")
        input("\n  Нажмите Enter для выхода...")
        sys.exit(1)

    print(f"  [✓] Найден: {vault_root}")
    print()

    wallet_path = vault_root / "wallet.vault"
    pending_dir = vault_root / "pending"
    signed_dir = vault_root / "signed"

    # --- Проверка pending TX ---
    pending_files = sorted(pending_dir.glob("*.json")) if pending_dir.exists() else []

    if not pending_files:
        print("  [*] Нет ожидающих транзакций для подписи.")
        print("  [*] Поместите файлы .json в папку:")
        print(f"      {pending_dir}")
        input("\n  Нажмите Enter для выхода...")
        sys.exit(0)

    print(f"  [*] Транзакций для подписи: {len(pending_files)}")
    print()
    for i, f in enumerate(pending_files, 1):
        print(f"      {i}. {f.name}")

    # --- Разблокировка ---
    print()
    print("  [*] Разблокировка кошелька...")
    password = getpass.getpass("  Пароль: ")

    km = KeyManager()
    try:
        address = km.decrypt_and_load(password, str(wallet_path))
        print(f"  [✓] Разблокирован: {address}")
    except ValueError as e:
        print(f"  [!] Ошибка: {e}")
        input("\n  Нажмите Enter для выхода...")
        sys.exit(1)

    # --- Подпись ---
    signed_count = 0
    for tx_file in pending_files:
        print()
        print(f"  ═══ {tx_file.name} ═══")

        try:
            with open(tx_file, "r", encoding="utf-8") as f:
                tx_json = f.read()
                tx_data = json.loads(tx_json)

            display_tx_details(tx_data)

            confirm = input("  Подписать? (y/n): ").strip().lower()
            if confirm != "y":
                print("  [—] Пропущено")
                continue

            # Подпись
            tx_request = TransactionSigner.deserialize_unsigned_tx(tx_json)
            raw_tx = TransactionSigner.sign_transaction(
                km.get_private_key(), tx_request
            )

            # Сохранение
            signed_dir.mkdir(exist_ok=True)
            signed_filename = tx_file.stem + "_signed.json"
            signed_path = signed_dir / signed_filename

            signed_data = {
                "type": "signed_transaction",
                "version": 1,
                "raw_tx": raw_tx,
                "original_file": tx_file.name,
                "from_address": address,
            }

            with open(signed_path, "w", encoding="utf-8") as f:
                json.dump(signed_data, f, indent=2)

            # Удаление из pending
            tx_file.unlink()

            print(f"  [✓] Подписано → {signed_filename}")
            signed_count += 1

        except Exception as e:
            print(f"  [!] Ошибка: {e}")

    # --- Итог ---
    km.clear()

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║  Подписано: {signed_count}/{len(pending_files)}" + " " * (42 - len(f"Подписано: {signed_count}/{len(pending_files)}")) + "║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print("  ║  Безопасно извлеките USB → перенесите на онлайн-ПК  ║")
    print("  ║  В десктоп-приложении: Подписать → Отправить в сеть  ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()
    input("  Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
