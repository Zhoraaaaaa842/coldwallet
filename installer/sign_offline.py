"""
ColdVault ETH — Утилита офлайн-подписи.
Запускается НА ОФЛАЙН-ПК (air-gapped) для подписи транзакций.

Использование:
    python sign_offline.py

Рабочий процесс:
1. Десктоп-приложение создаёт unsigned TX → сохраняет в pending/ на USB
2. USB переносится на офлайн-ПК
3. Эта утилита подписывает TX → сохраняет в signed/ на USB
4. USB переносится обратно на онлайн-ПК
5. Десктоп-приложение читает signed TX → отправляет в сеть
"""

import os
import sys
import json
import getpass
from pathlib import Path

# Поиск модулей: сначала в tools/, затем в родительской директории
script_dir = Path(__file__).parent
if (script_dir / "core").exists():
    sys.path.insert(0, str(script_dir))
    sys.path.insert(0, str(script_dir.parent))
else:
    sys.path.insert(0, str(script_dir.parent))

from core.key_manager import KeyManager
from core.transaction import TransactionSigner, TransactionRequest


def find_vault_root(start: Path) -> Path:
    """Ищет корень ColdVault (где wallet.vault)."""
    # Если запущено из tools/, vault на уровень выше
    if (start.parent / "wallet.vault").exists():
        return start.parent
    if (start / "wallet.vault").exists():
        return start
    raise FileNotFoundError("wallet.vault не найден. Запустите из папки ColdVault/tools/")


def print_header():
    print("\n" + "=" * 60)
    print("   ColdVault ETH — Офлайн подпись транзакций")
    print("=" * 60)
    print("   ⚠ Убедитесь, что этот ПК ОТКЛЮЧЁН от интернета!")
    print("=" * 60 + "\n")


def display_tx_details(tx_data: dict) -> None:
    """Показывает детали транзакции перед подписью."""
    tx = tx_data.get("tx", {})
    print("\n    ─── Детали транзакции ───")
    print(f"    Получатель:    {tx.get('to', 'N/A')}")

    value_wei = int(tx.get("value_wei", 0))
    value_eth = value_wei / 1e18
    print(f"    Сумма:         {value_eth:.8f} ETH ({value_wei} Wei)")

    print(f"    Nonce:         {tx.get('nonce', 'N/A')}")
    print(f"    Chain ID:      {tx.get('chain_id', 'N/A')}")
    print(f"    Gas Limit:     {tx.get('gas_limit', 'N/A')}")

    if tx.get("tx_type") == "eip1559":
        max_fee = int(tx.get("max_fee_per_gas", 0)) / 1e9
        priority = int(tx.get("max_priority_fee_per_gas", 0)) / 1e9
        print(f"    Тип:           EIP-1559")
        print(f"    Max Fee:       {max_fee:.4f} Gwei")
        print(f"    Priority Fee:  {priority:.4f} Gwei")
    else:
        gas_price = int(tx.get("gas_price", 0)) / 1e9
        print(f"    Тип:           Legacy")
        print(f"    Gas Price:     {gas_price:.4f} Gwei")

    if tx.get("data"):
        print(f"    Data:          {tx['data'][:40]}...")

    # Расчёт максимальной стоимости
    if tx.get("tx_type") == "eip1559":
        max_cost = value_wei + int(tx.get("gas_limit", 21000)) * int(tx.get("max_fee_per_gas", 0))
    else:
        max_cost = value_wei + int(tx.get("gas_limit", 21000)) * int(tx.get("gas_price", 0))
    print(f"    Макс. стоимость: {max_cost / 1e18:.8f} ETH")
    print("    ───────────────────────\n")


def main():
    print_header()

    # Находим корень ColdVault
    try:
        vault_root = find_vault_root(script_dir)
    except FileNotFoundError as e:
        print(f"    [!] {e}")
        sys.exit(1)

    wallet_path = vault_root / "wallet.vault"
    pending_dir = vault_root / "pending"
    signed_dir = vault_root / "signed"

    # Проверяем наличие pending TX
    pending_files = sorted(pending_dir.glob("*.json")) if pending_dir.exists() else []

    if not pending_files:
        print("    [*] Нет ожидающих транзакций для подписи.")
        print("    [*] Поместите файлы .json в папку pending/")
        sys.exit(0)

    print(f"    [*] Найдено транзакций для подписи: {len(pending_files)}\n")
    for i, f in enumerate(pending_files, 1):
        print(f"        {i}. {f.name}")

    # Разблокировка кошелька
    print(f"\n    [*] Разблокировка кошелька...")
    password = getpass.getpass("    Пароль: ")

    km = KeyManager()
    try:
        address = km.decrypt_and_load(password, str(wallet_path))
        print(f"    [✓] Кошелёк разблокирован: {address}\n")
    except ValueError as e:
        print(f"    [!] Ошибка: {e}")
        sys.exit(1)

    # Подпись каждой транзакции
    signed_count = 0
    for tx_file in pending_files:
        print(f"\n    ═══ Обработка: {tx_file.name} ═══")

        try:
            with open(tx_file, "r") as f:
                tx_json = f.read()
                tx_data = json.loads(tx_json)

            display_tx_details(tx_data)

            confirm = input("    Подписать? (y/n): ").strip().lower()
            if confirm != "y":
                print("    [—] Пропущено")
                continue

            # Десериализация и подпись
            tx_request = TransactionSigner.deserialize_unsigned_tx(tx_json)
            signer = TransactionSigner(km.get_private_key())
            raw_tx = signer.sign_transaction(tx_request)

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

            with open(signed_path, "w") as f:
                json.dump(signed_data, f, indent=2)

            # Удаление из pending
            tx_file.unlink()

            print(f"    [✓] Подписано → {signed_filename}")
            signed_count += 1

        except Exception as e:
            print(f"    [!] Ошибка: {e}")

    # Очистка
    km.clear()

    print(f"\n{'=' * 60}")
    print(f"    Подписано транзакций: {signed_count}/{len(pending_files)}")
    print(f"    Подписанные TX в: {signed_dir}")
    print(f"{'=' * 60}")
    print("    Безопасно извлеките USB и перенесите на онлайн-ПК.")
    print()


if __name__ == "__main__":
    main()
