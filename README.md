# ZhoraWallet — Холодный кошелёк Ethereum

> Программный cold wallet с air-gapped подписью транзакций через USB.  
> Крипто-ядро написано на **Rust (PyO3)** для безопасности памяти и производительности.

---

## Архитектура

```
┌──────────────────┐     USB      ┌───────────────────┐
│   Онлайн-ПК       │◄──────────►│   Офлайн-ПК         │
│   ZhoraWallet     │  pending/   │   SignOffline.exe   │
│                   │  signed/    │                     │
│  • Баланс         │             │  • Приватный ключ   │
│  • Создание TX    │             │  • Подпись TX       │
│  • Broadcast      │             │  • Мнемоника        │
└──────────────────┘             └───────────────────┘
```

Приватный ключ **никогда не покидает** офлайн-среду.

---

## Стек технологий

### Rust-ядро (`core-rust/`)

| Компонент | Крейт |
|---|---|
| PyO3-биндинги | `pyo3 = "0.21"` |
| BIP-39 мнемоника (24 слова) | `tiny-bip39` |
| HD деривация `m/44'/60'/0'/0/0` | `coins-bip32` |
| ECDSA secp256k1, адреса | `k256` |
| AES-256-GCM шифрование vault | `aes-gcm` |
| PBKDF2-SHA256 (600 000 итераций) | `pbkdf2` |
| Затирание секретов в памяти | `zeroize` |
| RLP-кодирование транзакций | `rlp` |

### Python GUI (`cold_wallet/`)

| Компонент | Библиотека |
|---|---|
| Десктоп-GUI | PyQt6 |
| Ethereum RPC | web3.py |
| QR-коды | qrcode + Pillow |
| Сборка EXE | PyInstaller |

---

## Структура проекта

```
coldwallet/
├── core-rust/                  ← Rust-ядро (PyO3)
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs              ← регистрация модуля coldvault_core
│       ├── key_manager.rs      ← BIP-39, HD деривация, AES-GCM, PBKDF2
│       ├── transaction.rs      ← EIP-1559 + Legacy подпись
│       ├── usb_manager.rs      ← path traversal защита
│       └── error.rs            ← VaultError → Python exceptions
│
├── cold_wallet/
│   ├── core/
│   │   ├── key_manager.py      ← тонкая обёртка над Rust
│   │   ├── transaction.py      ← тонкая обёртка над Rust
│   │   └── eth_network.py      ← RPC, баланс, nonce, broadcast
│   ├── storage/
│   │   └── usb_manager.py
│   └── gui/
│
├── installer/
├── build_all.py
└── requirements.txt
```

---

## Быстрый старт

### 1. Зависимости Python

```bash
pip install -r requirements.txt
```

### 2. Сборка Rust-ядра

```bash
# Установить Rust (если нет)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Установить maturin
pip install maturin

# Собрать и установить модуль
cd core-rust
maturin develop          # для разработки (debug)
# или
maturin build --release  # production .whl
pip install ../target/wheels/coldvault_core-*.whl --force-reinstall
```

### 3. Проверить сборку

```bash
python -c "from coldvault_core import KeyManager; km = KeyManager(); print(km.generate_wallet())"
```

### 4. Запуск приложения

```bash
python run_desktop.py
```

### 5. Сборка EXE

```bash
python build_all.py
```

| Флаг | Что собирает |
|---|---|
| `--desktop-only` | Только `ZhoraWallet.exe` |
| `--signer-only` | Только `SignOffline.exe` |
| `--installer-only` | Только `ZhoraUSB.exe` |
| `--no-clean` | Не удалять предыдущую сборку |

---

## Установка кошелька на USB

**Вариант A — через `ZhoraUSB.exe`**

1. Запустите `ZhoraUSB.exe` от имени администратора
2. Выберите флешку из списка
3. Нажмите **«Установить на флешку»** — подтвердите диалог
4. `SignOffline.exe` автоматически скопируется на флешку

**Вариант B — командная строка**

```bash
python installer/install_to_usb.py
```

> ❗ Запускайте `SignOffline.exe` только на **офлайн-ПК**.

---

## Рабочий процесс (отправка ETH)

```
[Онлайн-ПК] → USB → [Офлайн-ПК] → USB → [Онлайн-ПК]
Создать TX          Подписать TX         Broadcast
```

1. **ZhoraWallet** → вкладка «Отправить» → заполни адрес, сумму, gas → **«Создать TX → USB»**
2. Вставь USB в офлайн-ПК
3. **SignOffline.exe** → сканировать `pending/` → ввести пароль → подписать
4. Вставь USB обратно в онлайн-ПК
5. **ZhoraWallet** → сканировать `signed/` → **«Отправить в сеть»**

---

## Безопасность

| Компонент | Реализация |
|---|---|
| Шифрование vault | AES-256-GCM |
| Деривация пароля | PBKDF2-SHA256, 600 000 итераций |
| Хранение ключей | `Zeroizing<Vec<u8>>` + `ZeroizeOnDrop` |
| Защита от брутфорса | Блокировка после 5 неверных паролей |
| Мнемоника | BIP-39, 24 слова, 256 бит |
| HD деривация | BIP-44 `m/44'/60'/0'/0/0` |
| Транзакции | EIP-1559 + Legacy, ECDSA secp256k1 |
| Path traversal (USB) | Canonicalize + prefix-check |
| Атомарная запись vault | `.tmp` + `rename()` |

### Главные правила

- `SignOffline.exe` запускать **только на офлайн-ПК без интернета**
- Мнемонику (24 слова) хранить **на бумаге**, отдельно от флешки
- Флешка на онлайн-ПК — только для переноса `pending/` и `signed/`

Полный аудит: [SECURITY_AUDIT.md](SECURITY_AUDIT.md)

---

## Структура USB

```
USB/
├── SignOffline.exe
├── launch_signer.bat
└── ColdVault/
    ├── wallet.vault       ← зашифрованный кошелёк (AES-256-GCM)
    ├── config.json        ← chain_id, сеть
    ├── pending/           ← неподписанные TX
    └── signed/            ← подписанные TX
```

---

## Поддерживаемые сети

- Ethereum Mainnet (chain_id: 1)
- Sepolia Testnet (chain_id: 11155111)
- Custom RPC (в настройках)

---

> ⚠️ Это **программный** холодный кошелёк. Не заменяет аппаратные решения (Ledger, Trezor).  
> Используйте для обучения и умеренных сумм.
