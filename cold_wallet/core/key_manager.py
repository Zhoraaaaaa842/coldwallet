"""
ZhoraWallet ETH — Python-обёртка над Rust key_manager.
Тонкая прослойка: весь крипто-код теперь в coldvault_core (Rust).

Импортируй так же, как раньше:
    from cold_wallet.core.key_manager import KeyManager

Перед использованием собери Rust-ядро:
    cd core-rust && maturin develop --release
"""

from typing import Optional, Tuple

try:
    from coldvault_core import KeyManager as _RustKeyManager
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

# ────────────────────────────────────────────────────────────────────────────
# Если Rust-ядро не собрано — fallback на старую Python-реализацию
# ────────────────────────────────────────────────────────────────────────────
if not _RUST_AVAILABLE:
    import warnings
    warnings.warn(
        "coldvault_core (Rust) не найден. Используется медленный Python fallback. "
        "Запусти: cd core-rust && maturin develop --release",
        RuntimeWarning,
        stacklevel=2,
    )
    # Импортируем старую реализацию под другим именем для fallback
    from cold_wallet.core._key_manager_py import KeyManager  # type: ignore
else:
    class KeyManager(_RustKeyManager):  # type: ignore[misc]
        """
        ETH KeyManager — Rust-реализация через PyO3.

        Методы:
            generate_wallet()                     -> (mnemonic: str, address: str)
            import_from_mnemonic(mnemonic: str)   -> address: str
            import_from_private_key(hex: str)     -> address: str
            encrypt_and_save(password, filepath)  -> None
            decrypt_and_load(password, filepath)  -> address: str
            get_private_key()                     -> bytes
            get_address()                         -> str
            remaining_attempts()                  -> int
            clear()                               -> None

        Пример:
            km = KeyManager()
            mnemonic, address = km.generate_wallet()
            km.encrypt_and_save("my_password", "/mnt/usb/wallet.vault")

            km2 = KeyManager()
            address = km2.decrypt_and_load("my_password", "/mnt/usb/wallet.vault")
        """
        # Дополнительные удобные свойства для совместимости с Python GUI

        @property
        def address(self) -> Optional[str]:
            """Адрес текущего кошелька или None."""
            try:
                return self.get_address()
            except RuntimeError:
                return None

        @property
        def private_key(self) -> Optional[bytes]:
            """Приватный ключ или None (для совместимости с Python GUI)."""
            try:
                return bytes(self.get_private_key())
            except RuntimeError:
                return None


__all__ = ["KeyManager"]
