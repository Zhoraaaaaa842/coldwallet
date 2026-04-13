"""
ZhoraWallet ETH — Python-обёртка над Rust KeyManager.

Если Rust-крейт собран (coldvault_core доступен), используем его.
Иначе — fallback на чистый Python для разработки без Rust toolchain.
"""

try:
    # PyO3-классы не поддерживают наследование — просто переэкспортируем
    from coldvault_core import KeyManager  # type: ignore
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

if not _RUST_AVAILABLE:
    # --- Fallback Python-реализация (для среды без Rust) ---
    import os
    import json
    import ctypes
    import secrets
    from typing import Optional, Tuple

    from eth_account import Account
    from mnemonic import Mnemonic
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes

    Account.enable_unaudited_hdwallet_features()

    PBKDF2_ITERATIONS = 600_000
    PBKDF2_ITERATIONS_MIN = 600_000
    SALT_SIZE = 32
    NONCE_SIZE = 12
    KEY_SIZE = 32
    MAX_FAILED_ATTEMPTS = 5
    MIN_PASSWORD_LENGTH = 8

    def _secure_zero(data) -> None:
        """
        FIX: обнуляет bytearray напрямую в памяти (не создаёт копию).
        Принимает bytes или bytearray.
        """
        if not data:
            return
        try:
            if isinstance(data, (bytes, bytearray)):
                buf = (ctypes.c_char * len(data)).from_buffer(bytearray(data))
                ctypes.memset(buf, 0, len(data))
        except Exception:
            pass

    class KeyManager:  # type: ignore[no-redef]
        """Python fallback — используется когда Rust крейт не собран."""

        def __init__(self):
            self._mnemo = Mnemonic("english")
            self._private_key: Optional[bytearray] = None
            self._address: Optional[str] = None
            self._mnemonic: Optional[str] = None
            self._failed_attempts: int = 0

        @property
        def address(self) -> Optional[str]:
            return self._address

        @property
        def mnemonic(self) -> Optional[str]:
            return self._mnemonic

        @property
        def remaining_attempts(self) -> int:
            return MAX_FAILED_ATTEMPTS - self._failed_attempts

        def generate_wallet(self) -> Tuple[str, str]:
            self._mnemonic = self._mnemo.generate(strength=256)
            acct = Account.from_mnemonic(
                self._mnemonic, account_path="m/44'/60'/0'/0/0"
            )
            self._private_key = bytearray(acct.key)
            self._address = acct.address
            return self._mnemonic, self._address

        def import_from_mnemonic(self, mnemonic: str) -> str:
            if not self._mnemo.check(mnemonic):
                raise ValueError("Неверная мнемоническая фраза")
            acct = Account.from_mnemonic(
                mnemonic, account_path="m/44'/60'/0'/0/0"
            )
            self._private_key = bytearray(acct.key)
            self._address = acct.address
            self._mnemonic = mnemonic
            return self._address

        def import_from_private_key(self, private_key_hex: str) -> str:
            if private_key_hex.startswith("0x"):
                private_key_hex = private_key_hex[2:]
            pk_bytes = bytes.fromhex(private_key_hex)
            if len(pk_bytes) != 32:
                raise ValueError("Приватный ключ должен быть 32 байта")
            acct = Account.from_key(pk_bytes)
            self._private_key = bytearray(acct.key)
            self._address = acct.address
            self._mnemonic = None
            return self._address

        def _derive_encryption_key(self, password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytearray:
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_SIZE,
                salt=salt,
                iterations=iterations,
            )
            return bytearray(kdf.derive(password.encode("utf-8")))

        def encrypt_and_save(self, password: str, filepath: str) -> None:
            if self._private_key is None:
                raise RuntimeError("Ключ не загружен.")
            if not password:
                raise ValueError("Пароль не может быть пустым")
            # FIX: минимальная длина пароля
            if len(password) < MIN_PASSWORD_LENGTH:
                raise ValueError(f"Пароль должен содержать не менее {MIN_PASSWORD_LENGTH} символов")
            salt = secrets.token_bytes(SALT_SIZE)
            nonce = secrets.token_bytes(NONCE_SIZE)
            enc_key = self._derive_encryption_key(password, salt)
            payload = {"private_key": bytes(self._private_key).hex()}
            if self._mnemonic:
                payload["mnemonic"] = self._mnemonic
            plaintext = bytearray(json.dumps(payload).encode("utf-8"))
            aesgcm = AESGCM(bytes(enc_key))
            aad = self._address.encode("utf-8") if self._address else None
            ciphertext = aesgcm.encrypt(nonce, bytes(plaintext), aad)
            wallet_data = {
                "version": 1, "address": self._address,
                "salt": salt.hex(), "nonce": nonce.hex(),
                "ciphertext": ciphertext.hex(),
                "iterations": PBKDF2_ITERATIONS,
                "has_mnemonic": self._mnemonic is not None,
            }
            tmp_path = filepath + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(wallet_data, f, indent=2)
            os.replace(tmp_path, filepath)
            _secure_zero(plaintext)
            _secure_zero(enc_key)

        def decrypt_and_load(self, password: str, filepath: str) -> str:
            if self._failed_attempts >= MAX_FAILED_ATTEMPTS:
                raise PermissionError(
                    f"Превышено максимальное число попыток ({MAX_FAILED_ATTEMPTS})."
                )
            with open(filepath, "r", encoding="utf-8") as f:
                wallet_data = json.load(f)
            if wallet_data.get("version") != 1:
                raise ValueError("Неподдерживаемая версия формата кошелька")
            salt = bytes.fromhex(wallet_data["salt"])
            nonce = bytes.fromhex(wallet_data["nonce"])
            ciphertext = bytes.fromhex(wallet_data["ciphertext"])
            address = wallet_data["address"]
            file_iterations = wallet_data.get("iterations", PBKDF2_ITERATIONS)
            iterations = max(int(file_iterations), PBKDF2_ITERATIONS_MIN)
            enc_key = self._derive_encryption_key(password, salt, iterations)
            aesgcm = AESGCM(bytes(enc_key))
            aad = address.encode("utf-8")
            try:
                plaintext = bytearray(aesgcm.decrypt(nonce, ciphertext, aad))
            except Exception:
                self._failed_attempts += 1
                _secure_zero(enc_key)
                remaining = MAX_FAILED_ATTEMPTS - self._failed_attempts
                raise ValueError(f"Неверный пароль. Осталось попыток: {remaining}")
            payload = json.loads(bytes(plaintext).decode("utf-8"))
            self._private_key = bytearray(bytes.fromhex(payload["private_key"]))
            self._address = address
            self._mnemonic = payload.get("mnemonic")
            self._failed_attempts = 0
            acct = Account.from_key(bytes(self._private_key))
            if acct.address.lower() != address.lower():
                self.clear()
                raise ValueError("Ошибка целостности: адрес не совпадает")
            _secure_zero(plaintext)
            _secure_zero(enc_key)
            return self._address

        @property
        def private_key(self) -> Optional[bytes]:
            return bytes(self._private_key) if self._private_key is not None else None

        def get_private_key(self) -> bytes:
            if self._private_key is None:
                raise RuntimeError("Ключ не загружен")
            return bytes(self._private_key)

        def clear(self) -> None:
            if self._private_key is not None:
                _secure_zero(self._private_key)
            self._private_key = None
            self._address = None
            self._mnemonic = None
            self._failed_attempts = 0
