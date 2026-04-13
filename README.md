# ZhoraWallet — Холодный кошелёк Ethereum

> Десктопный cold wallet с air-gapped подписью транзакций через USB.
> Построен на **Tauri 2.0 + Vue 3 + Rust** для максимальной безопасности и современного UI.

---

## Архитектура

```
┌──────────────────┐     USB      ┌───────────────────┐
│   Онлайн-ПК       │◄──────────►│   Офлайн-ПК         │
│   ZhoraWallet     │  pending/   │   SignOffline       │
│   (Tauri App)     │  signed/    │   (Tauri App)       │
│  • Баланс         │             │  • Приватный ключ   │
│  • Создание TX    │             │  • Подпись TX       │
│  • Broadcast      │             │  • Мнемоника        │
└──────────────────┘             └───────────────────┘
```

Приватный ключ **никогда не покидает** офлайн-среду.

---

## Стек технологий

### Frontend (`zhorawallet-tauri/`)

| Компонент | Технология |
|---|---|
| UI Framework | Vue 3 + TypeScript |
| Стили | TailwindCSS |
| Сборка | Vite |
| State Management | Pinia |
| Роутинг | Vue Router |

### Backend (Tauri Rust Core)

| Компонент | Крейт |
|---|---|
| Tauri Desktop | `tauri = "2.0"` |
| BIP-39 мнемоника (24 слова) | `bip39` |
| ECDSA secp256k1, адреса | `k256` |
| AES-256-GCM шифрование vault | `aes-gcm` |
| PBKDF2-SHA256 (600 000 итераций) | `pbkdf2` |
| Keccak-256 для адресов | `tiny-keccak` |
| HTTP запросы (RPC) | `reqwest` |
| QR-коды | `qrcode-generator` |

---

## Структура проекта

```
coldwallet/
├── zhorawallet-tauri/            ← Tauri приложение (Vue 3 + Rust)
│   ├── src/                      ← Frontend (Vue + TypeScript)
│   │   ├── components/           ← Vue компоненты
│   │   ├── views/                ← Страницы (Dashboard, Send, Receive...)
│   │   ├── stores/               ← Pinia stores
│   │   └── composables/          ← Vue composables
│   ├── src-tauri/                ← Tauri Backend (Rust)
│   │   ├── src/
│   │   │   ├── commands.rs       ← Tauri команды (17 штук)
│   │   │   ├── crypto.rs         ← Криптография (BIP-39, AES-GCM, signing)
│   │   │   ├── network.rs        ← Ethereum RPC
│   │   │   ├── usb.rs            ← USB детекция и файловые операции
│   │   │   └── state.rs          ← AppState (состояние приложения)
│   │   ├── Cargo.toml
│   │   └── tauri.conf.json
│   └── package.json
│
├── core-rust/                    ← Rust крипто-ядро (для справки)
│   └── src/                      ← Полная реализация BIP-32/44, signing
│
├── .gitignore
├── SECURITY_AUDIT.md
└── CLEAN_HISTORY.md
```

---

## Быстрый старт

### Предварительные требования

- **Rust**: https://www.rust-lang.org/tools/install
- **Node.js**: https://nodejs.org/ (v18+)

### 1. Установка зависимостей

```bash
cd zhorawallet-tauri
npm install
```

### 2. Запуск в режиме разработки

```bash
npm run tauri dev
```

### 3. Сборка приложения

```bash
npm run tauri build
```

Собранные файлы появятся в `zhorawallet-tauri/src-tauri/target/release/bundle/`

---

## Рабочий процесс (отправка ETH)

```
[Онлайн-ПК] → USB → [Офлайн-ПК] → USB → [Онлайн-ПК]
Создать TX          Подписать TX         Broadcast
```

1. **ZhoraWallet** → вкладка «Отправить» → заполни адрес, сумму, gas → **«Создать TX → USB»**
2. Вставь USB в офлайн-ПК
3. **ZhoraWallet (офлайн)** → сканировать `pending/` → ввести пароль → подписать
4. Вставь USB обратно в онлайн-ПК
5. **ZhoraWallet** → сканировать `signed/` → **«Отправить в сеть»**

---

## Безопасность

| Компонент | Реализация |
|---|---|
| Шифрование vault | AES-256-GCM |
| Деривация пароля | PBKDF2-SHA256, 600 000 итераций |
| Хранение ключей | BIP-39 мнемоника (24 слова) |
| HD деривация | BIP-44 `m/44'/60'/0'/0/0` |
| Транзакции | EIP-1559 + Legacy, ECDSA secp256k1 |
| Path traversal (USB) | Canonicalize + prefix-check |
| Атомарная запись vault | `.tmp` + `rename()` |

### Главные правила

- Запускать приложение на офлайн-ПК **только без интернета**
- Мнемонику (24 слова) хранить **на бумаге**, отдельно от USB
- USB-носитель — только для переноса `pending/` и `signed/`

Полный аудит: [SECURITY_AUDIT.md](SECURITY_AUDIT.md)

---

## Структура USB

```
USB/
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
