# Сборка Rust-крейта coldvault_core

## Требования

```bash
# 1. Установить Rust (если не установлен)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 2. Установить maturin
pip install maturin

# 3. (Опционально) установить maturin develop для быстрой итерации
pip install maturin[patchelf]  # Linux
```

## Разработка (debug-сборка)

```bash
cd core-rust

# Собирает .so/.pyd и устанавливает в текущий venv
maturin develop

# Или с флагом для корректной сборки на Linux
maturin develop --release
```

## Production-сборка

```bash
cd core-rust

# Собирает wheel для текущей платформы
maturin build --release

# Устанавливает wheel в venv
pip install ../target/wheels/coldvault_core-*.whl --force-reinstall
```

## Тестирование

```bash
# Rust unit-тесты
cd core-rust
cargo test

# Python интеграционные тесты
python -c "
from coldvault_core import KeyManager
km = KeyManager()
mnemonic, address = km.generate_wallet()
print(f'Address: {address}')
print(f'Mnemonic words: {len(mnemonic.split())}')
assert address.startswith('0x')
assert len(mnemonic.split()) == 24
print('OK: generate_wallet')

import tempfile, os
with tempfile.NamedTemporaryFile(suffix='.vault', delete=False) as f:
    path = f.name

km.encrypt_and_save('test_password_123', path)
km.clear()
assert km.address is None

km2 = KeyManager()
addr = km2.decrypt_and_load('test_password_123', path)
print(f'Loaded address: {addr}')
assert addr == address
print('OK: encrypt/decrypt round-trip')
os.unlink(path)

print('Все тесты пройдены!')
"
```

## Структура после сборки

```
coldwallet/
├── core-rust/
│   ├── Cargo.toml
│   ├── pyproject.toml
│   ├── BUILD.md
│   └── src/
│       ├── lib.rs
│       ├── error.rs
│       ├── key_manager.rs
│       ├── transaction.rs
│       └── usb_manager.rs
├── cold_wallet/core/
│   ├── key_manager.py   ← обёртка (импортирует Rust или fallback)
│   └── transaction.py   ← обёртка
└── target/wheels/
    └── coldvault_core-0.1.0-*.whl
```

## Проверка что Rust-крейт активен

```python
import coldvault_core
print(dir(coldvault_core))  # должен показать KeyManager, TransactionSigner и т.д.
```

## Устранение проблем

**`error: linker 'cc' not found`** (Linux):
```bash
sudo apt install build-essential
```

**`maturin: command not found`**:
```bash
pip install maturin
```

**`coins-bip32` ошибки компиляции** — убедитесь что Rust >= 1.75:
```bash
rustup update stable
```
