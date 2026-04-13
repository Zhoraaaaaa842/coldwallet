# ZhoraWallet - Ethereum Cold Wallet (Tauri + Vue.js)

Холодный кошелёк Ethereum с air-gapped подписью через USB накопитель.

## Архитектура

- **Фронтенд**: Vue.js 3 + TypeScript + TailwindCSS
- **Бэкенд**: Rust (Tauri 2.0)
- **Криптография**: bip39, aes-gcm, pbkdf2, sha2
- **Сеть**: reqwest для JSON-RPC вызовов

## Структура проекта

```
zhorawallet-tauri/
├── src/
│   ├── components/        # Vue компоненты
│   │   ├── Layout.vue
│   │   ├── PasswordDialog.vue
│   │   ├── WalletInitDialog.vue
│   │   └── TransactionItem.vue
│   ├── views/            # Страницы приложения
│   │   ├── Dashboard.vue
│   │   ├── Send.vue
│   │   ├── Receive.vue
│   │   ├── SignBroadcast.vue
│   │   └── Settings.vue
│   ├── stores/           # Pinia хранилища
│   │   └── wallet.ts
│   ├── router/           # Vue Router
│   │   └── index.ts
│   ├── types/            # TypeScript типы
│   │   └── index.ts
│   ├── assets/           # CSS и ресурсы
│   │   └── main.css
│   ├── App.vue
│   ├── main.ts
│   └── src-tauri/        # Tauri бэкенд (Rust)
│       ├── src/
│       │   ├── commands.rs    # Tauri команды
│       │   ├── crypto.rs      # Криптография
│       │   ├── usb.rs         # Работа с USB
│       │   ├── network.rs     # Сетевые вызовы
│       │   └── state.rs       # Состояние приложения
│       ├── Cargo.toml
│       ├── tauri.conf.json
│       └── main.rs
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## Установка зависимостей

### Для разработки

```bash
npm install
```

### Для Rust бэкенда

Убедитесь что установлен Rust и Tauri CLI:

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Tauri CLI
cargo install tauri-cli --version "^2.0.0"
```

## Запуск в режиме разработки

```bash
# Фронтенд + бэкенд
npm run tauri:dev

# Или только фронтенд
npm run dev
```

## Сборка приложения

```bash
# Сборка всех EXE
npm run tauri:build

# Результат в src/src-tauri/target/release/bundle/
```

## Функциональность

### 5 страниц приложения:

1. **Dashboard (Кошелёк)**
   - Баланс в ETH и RUB
   - Адрес кошелька
   - Информационные карточки (nonce, сеть, газ, USB статус)
   - История транзакций с фильтрами

2. **Send (Отправить ETH)**
   - Форма ввода адреса получателя
   - Ввод суммы
   - Настройки газа (EIP-1559 / Legacy)
   - Создание транзакции и сохранение на USB

3. **Receive (Получить ETH)**
   - Генерация QR-кода для адреса
   - Сканирование входящих QR-кодов
   - Сохранение QR в PNG

4. **Sign & Broadcast (Подписать & Отправить)**
   - Сканирование pending/ транзакций с USB
   - Подпись транзакций приватным ключом
   - Сканирование signed/ транзакций
   - Отправка в Ethereum сеть
   - Лог операций

5. **Settings (Настройки)**
   - Информация о кошельке
   - Блокировка/разблокировка
   - Резервная копия мнемонической фразы
   - RPC настройки

## Дизайн

Тёмная тема в стиле Ledger Live:
- Фон: `#0F0F13` (primary), `#17171C` (secondary)
- Акцент: `#A855F7` (purple)
- Успех: `#22C55E` (green)
- Ошибка: `#EF4444` (red)
- Скруглённые углы (8px-20px)
- Кастомный scrollbar

## Криптография

- **BIP-39**: 24-словная мнемоническая фраза
- **BIP-32**: HD деривация `m/44'/60'/0'/0/0`
- **AES-256-GCM**: Шифрование vault файла
- **PBKDF2-SHA256**: 600,000 итераций для ключа
- **secp256k1**: ECDSA подписи транзакций

## Безопасность

- Приватный ключ никогда не покидает оффлайн устройство
- Air-gapped архитектура через USB
- Шифрование хранилища паролем
- Защита от перебора паролей

## Workflow

### Онлайн PC (ZhoraWallet.exe):
1. Проверка баланса
2. Создание unsigned транзакции → `pending/` на USB
3. Чтение signed транзакций с USB → `signed/`
4. Broadcast в Ethereum сеть

### Оффлайн PC (SignOffline.exe):
1. Чтение unsigned транзакций с USB → `pending/`
2. Подпись приватным ключом → `signed/` на USB
3. Удаление из `pending/`

## Лицензия

MIT
