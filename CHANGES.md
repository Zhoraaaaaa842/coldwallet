# Changelog — ZhoraWallet

---

## [V0.0.2] — 2026-07-06

### 🐛 Исправления

#### 🔌 USB-детекция (`usb.rs`)
- **Фикс:** при отсутствии флешки приложение ошибочно показывало что USB подключён
- Добавлена `is_removable_drive()` — использует Windows API `GetDriveTypeW()`, теперь определяются только съёмные носители (`DRIVE_REMOVABLE = 2`)
- Добавлена `check_usb_detailed()` со структурой `UsbStatus { path, has_vault, needs_format }`
- Добавлена зависимость `winapi` в `Cargo.toml`

#### 🖼️ UI предупреждений
- **`Dashboard.vue`** — текст "USB Disconnected" → "Вставьте флешку"; добавлены блоки "⚠ Требуется форматирование USB" и "✓ Wallet.vault найден"
- **`TitleBar.vue`** — текст "USB Disconnected" → "Вставьте флешку"
- **`Settings.vue`** — "УСБ не обнаружен" → "Вставьте флешку"; добавлены информативные блоки статуса USB

#### 💻 TypeScript (`wallet.ts`)
- Добавлены реактивные переменные: `usbPath`, `usbHasVault`, `usbNeedsFormat`
- Обновлена `checkUsbStatus()` — обработка расширенного статуса USB

### 📄 Измененные файлы
1. `zhorawallet-tauri/src-tauri/src/usb.rs`
2. `zhorawallet-tauri/src-tauri/src/commands.rs`
3. `zhorawallet-tauri/src-tauri/Cargo.toml`
4. `zhorawallet-tauri/src/stores/wallet.ts`
5. `zhorawallet-tauri/src/views/Dashboard.vue`
6. `zhorawallet-tauri/src/views/Settings.vue`
7. `zhorawallet-tauri/src/components/TitleBar.vue`

---

## [V0.0.1] — 2026-04-11

- Первый релиз: базовая air-gapped архитектура
- Tauri 2.0 + Vue 3 + Rust
- BIP-39 (24 слова), AES-256-GCM, EIP-1559
- USB-перенос `pending/` и `signed/` транзакций
