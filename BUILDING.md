# Сборка Rust-ядра (coldvault-core)

## Требования

```bash
# 1. Установить Rust (если нет)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# 2. Установить maturin
pip install maturin

# 3. Убедиться, что Python >= 3.10
python --version
```

## Разработческая сборка (быстрая, debug + release)

```bash
cd core-rust
maturin develop --release
```

После этого в текущем virtualenv появится модуль `coldvault_core`:

```python
from coldvault_core import KeyManager, TransactionRequest, TransactionSigner
```

## Production wheel

```bash
cd core-rust
maturin build --release
# Wheel будет в core-rust/target/wheels/
pip install target/wheels/coldvault_core-*.whl
```

## Запуск тестов Rust

```bash
cd core-rust
cargo test
```

## Запуск тестов Python

```bash
# После maturin develop
python -m pytest tests/ -v
```

## Проверка что модуль загружен правильно

```python
import coldvault_core
print(coldvault_core.__version__)  # 0.1.0

km = coldvault_core.KeyManager()
mnemonic, address = km.generate_wallet()
print(address)  # 0x...
```

## Типичные ошибки

### `ModuleNotFoundError: No module named 'coldvault_core'`
Запусти `maturin develop` внутри активного virtualenv.

### `error[E0432]: unresolved import 'coins_bip32::enc::MainnetEncoder'`
Проверь версии крейтов в Cargo.toml — coins-bip32 API менялся между 0.8/0.9.

### `maturin: command not found`
```bash
pip install maturin
# или
pipx install maturin
```

## Структура после сборки

```
coldwallet/
├── core-rust/                  ← Rust-ядро
│   ├── Cargo.toml
│   ├── pyproject.toml
│   └── src/
│       ├── lib.rs              ← регистрация PyO3 модуля
│       ├── key_manager.rs      ← BIP-39/44, AES-256-GCM, PBKDF2
│       ├── transaction.rs      ← EIP-1559 + Legacy подпись
│       └── usb_manager.rs      ← path traversal защита
├── cold_wallet/core/
│   ├── key_manager.py          ← тонкая обёртка (import из Rust)
│   └── transaction.py          ← тонкая обёртка (import из Rust)
└── BUILDING.md                 ← эта инструкция
```
