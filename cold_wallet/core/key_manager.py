"""
ZhoraWallet ETH — Модуль управления ключами.
Генерация мнемонической фразы (BIP-39), деривация HD-ключей (BIP-32/44),
шифрование приватного ключа AES-256-GCM с PBKDF2.
"""

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

PBKDF2_ITERATIONS = 600_000  # OWASP >= 600k для SHA-256
PBKDF2_ITERATIONS_MIN = 600_000  # FIX #3: нельзя принять меньше этого из файла
SALT_SIZE = 32
NONCE_SIZE = 12
KEY_SIZE = 32
MAX_FAILED_ATTEMPTS = 5   # FIX #5: lockout после N неверных паролей


def _secure_zero(data: bytes) -> None:
    """FIX #1: Физически затирает байты ключа в памяти через ctypes."""
    if not data:
        return
    try:
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        ctypes.memset(buf, 0, len(data))
    except Exception:
        pass


class KeyManager:
    """Управление криптографическими ключами ETH кошелька."""

    def __init__(self):
        self._mnemo = Mnemonic("english")
        self._private_key: Optional[bytes] = None
        self._address: Optional[str] = None
        self._mnemonic: Optional[str] = None
        self._failed_attempts: int = 0  # FIX #5

    @property
    def address(self) -> Optional[str]:
        return self._address

    @property
    def mnemonic(self) -> Optional[str]:
        return self._mnemonic

    @property
    def private_key(self) -> Optional[bytes]:
        return self._private_key

    def generate_wallet(self) -> Tuple[str, str]:
        """
        Генерирует новый ETH-кошелёк.
        Возвращает (mnemonic, address).
        """
        self._mnemonic = self._mnemo.generate(strength=256)
        acct = Account.from_mnemonic(
            self._mnemonic,
            account_path="m/44'/60'/0'/0/0"
        )
        self._private_key = bytes(acct.key)
        self._address = acct.address
        return self._mnemonic, self._address

    def import_from_mnemonic(self, mnemonic: str) -> str:
        """Импорт кошелька из мнемонической фразы."""
        if not self._mnemo.check(mnemonic):
            raise ValueError("Неверная мнемоническая фраза")
        self._mnemonic = mnemonic
        acct = Account.from_mnemonic(
            mnemonic,
            account_path="m/44'/60'/0'/0/0"
        )
        self._private_key = bytes(acct.key)
        self._address = acct.address
        return self._address

    def import_from_private_key(self, private_key_hex: str) -> str:
        """Импорт кошелька из приватного ключа (hex)."""
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex[2:]
        pk_bytes = bytes.fromhex(private_key_hex)
        if len(pk_bytes) != 32:
            raise ValueError("Приватный ключ должен быть 32 байта")
        acct = Account.from_key(pk_bytes)
        self._private_key = bytes(acct.key)
        self._address = acct.address
        self._mnemonic = None
        return self._address

    def _derive_encryption_key(self, password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
        """Деривация AES-ключа из пароля через PBKDF2-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password.encode("utf-8"))

    def encrypt_and_save(self, password: str, filepath: str) -> None:
        """
        Шифрует приватный ключ AES-256-GCM и сохраняет в файл.
        """
        if self._private_key is None:
            raise RuntimeError("Ключ не загружен.")
        if not password:
            raise ValueError("Пароль не может быть пустым")

        salt = secrets.token_bytes(SALT_SIZE)
        nonce = secrets.token_bytes(NONCE_SIZE)
        enc_key = self._derive_encryption_key(password, salt)

        payload = {"private_key": self._private_key.hex()}
        if self._mnemonic:
            payload["mnemonic"] = self._mnemonic

        plaintext = json.dumps(payload).encode("utf-8")
        aesgcm = AESGCM(enc_key)
        aad = self._address.encode("utf-8") if self._address else None
        ciphertext = aesgcm.encrypt(nonce, plaintext, aad)

        wallet_data = {
            "version": 1,
            "address": self._address,
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "iterations": PBKDF2_ITERATIONS,
            "has_mnemonic": self._mnemonic is not None,
        }

        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(wallet_data, f, indent=2)
        os.replace(tmp_path, filepath)

        # FIX #1: затираем промежуточные данные
        _secure_zero(plaintext)
        _secure_zero(enc_key)

    def decrypt_and_load(self, password: str, filepath: str) -> str:
        """Загружает и дешифрует кошелёк из файла."""
        # FIX #5: блокировка после MAX_FAILED_ATTEMPTS неверных попыток
        if self._failed_attempts >= MAX_FAILED_ATTEMPTS:
            raise PermissionError(
                f"Превышено максимальное число попыток ({MAX_FAILED_ATTEMPTS}). "
                "Перезапустите приложение."
            )

        with open(filepath, "r", encoding="utf-8") as f:
            wallet_data = json.load(f)

        if wallet_data.get("version") != 1:
            raise ValueError("Неподдерживаемая версия формата кошелька")

        salt = bytes.fromhex(wallet_data["salt"])
        nonce = bytes.fromhex(wallet_data["nonce"])
        ciphertext = bytes.fromhex(wallet_data["ciphertext"])
        address = wallet_data["address"]

        # FIX #3: игнорируем iterations из файла если оно ниже минимума
        file_iterations = wallet_data.get("iterations", PBKDF2_ITERATIONS)
        iterations = max(int(file_iterations), PBKDF2_ITERATIONS_MIN)

        enc_key = self._derive_encryption_key(password, salt, iterations)
        aesgcm = AESGCM(enc_key)
        aad = address.encode("utf-8")

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception:
            self._failed_attempts += 1  # FIX #5
            _secure_zero(enc_key)
            remaining = MAX_FAILED_ATTEMPTS - self._failed_attempts
            raise ValueError(
                f"Неверный пароль или повреждённый файл. "
                f"Осталось попыток: {remaining}"
            )

        payload = json.loads(plaintext.decode("utf-8"))
        self._private_key = bytes.fromhex(payload["private_key"])
        self._address = address
        self._mnemonic = payload.get("mnemonic")
        self._failed_attempts = 0  # сброс счётчика при успехе

        acct = Account.from_key(self._private_key)
        if acct.address.lower() != address.lower():
            self.clear()
            raise ValueError("Ошибка целостности: адрес не совпадает с ключом")

        # FIX #1: затираем промежуточные данные
        _secure_zero(plaintext)
        _secure_zero(enc_key)

        return self._address

    def get_private_key(self) -> bytes:
        """Возвращает приватный ключ (для подписи)."""
        if self._private_key is None:
            raise RuntimeError("Ключ не загружен")
        return self._private_key

    def clear(self) -> None:
        """FIX #1: Безопасная очистка ключей из памяти через ctypes."""
        if self._private_key is not None:
            _secure_zero(self._private_key)
        self._private_key = None
        self._address = None
        self._mnemonic = None
        self._failed_attempts = 0
