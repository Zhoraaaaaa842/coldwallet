"""
ColdVault ETH — Модуль управления ключами.
Генерация мнемонической фразы (BIP-39), деривация HD-ключей (BIP-32/44),
шифрование приватного ключа AES-256-GCM с PBKDF2.
"""

import os
import json
import hashlib
import secrets
from typing import Optional, Tuple

from eth_account import Account
from eth_keys import keys
from mnemonic import Mnemonic
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# Включаем HD-кошелёк в eth_account
Account.enable_unaudited_hdwallet_features()

# Константы безопасности
PBKDF2_ITERATIONS = 600_000  # OWASP рекомендует >= 600k для SHA-256
SALT_SIZE = 32               # 256 бит
NONCE_SIZE = 12              # 96 бит для AES-GCM
KEY_SIZE = 32                # AES-256


class KeyManager:
    """Управление криптографическими ключами ETH кошелька."""

    def __init__(self):
        self._mnemo = Mnemonic("english")
        self._private_key: Optional[bytes] = None
        self._address: Optional[str] = None
        self._mnemonic: Optional[str] = None

    @property
    def address(self) -> Optional[str]:
        return self._address

    @property
    def mnemonic(self) -> Optional[str]:
        return self._mnemonic

    @property
    def private_key(self) -> Optional[bytes]:
        """Приватный ключ (bytes) или None если кошелёк не разблокирован."""
        return self._private_key

    def generate_wallet(self) -> Tuple[str, str]:
        """
        Генерирует новый ETH-кошелёк.
        Возвращает (mnemonic, address).
        Мнемоника — 24 слова (256 бит энтропии).
        Деривация по BIP-44: m/44'/60'/0'/0/0
        """
        self._mnemonic = self._mnemo.generate(strength=256)
        acct = Account.from_mnemonic(
            self._mnemonic,
            account_path="m/44'/60'/0'/0/0"
        )
        self._private_key = acct.key
        self._address = acct.address
        return self._mnemonic, self._address

    def import_from_mnemonic(self, mnemonic: str) -> str:
        """Импорт кошелька из мнемонической фразы. Возвращает адрес."""
        if not self._mnemo.check(mnemonic):
            raise ValueError("Неверная мнемоническая фраза")
        self._mnemonic = mnemonic
        acct = Account.from_mnemonic(
            mnemonic,
            account_path="m/44'/60'/0'/0/0"
        )
        self._private_key = acct.key
        self._address = acct.address
        return self._address

    def import_from_private_key(self, private_key_hex: str) -> str:
        """Импорт кошелька из приватного ключа (hex). Возвращает адрес."""
        if private_key_hex.startswith("0x"):
            private_key_hex = private_key_hex[2:]
        pk_bytes = bytes.fromhex(private_key_hex)
        if len(pk_bytes) != 32:
            raise ValueError("Приватный ключ должен быть 32 байта")
        acct = Account.from_key(pk_bytes)
        self._private_key = acct.key
        self._address = acct.address
        self._mnemonic = None
        return self._address

    def _derive_encryption_key(self, password: str, salt: bytes) -> bytes:
        """Деривация AES-ключа из пароля через PBKDF2-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))

    def encrypt_and_save(self, password: str, filepath: str) -> None:
        """
        Шифрует приватный ключ AES-256-GCM и сохраняет в файл.
        Формат файла (JSON):
        {
            "version": 1,
            "address": "0x...",
            "salt": hex,
            "nonce": hex,
            "ciphertext": hex,
            "iterations": int,
            "has_mnemonic": bool
        }
        """
        if self._private_key is None:
            raise RuntimeError("Ключ не загружен. Сначала сгенерируйте или импортируйте кошелёк.")

        # FIX #5: пароль не должен быть пустым
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

    def decrypt_and_load(self, password: str, filepath: str) -> str:
        """Загружает и дешифрует кошелёк из файла. Возвращает адрес."""
        with open(filepath, "r", encoding="utf-8") as f:
            wallet_data = json.load(f)

        if wallet_data.get("version") != 1:
            raise ValueError("Неподдерживаемая версия формата кошелька")

        salt = bytes.fromhex(wallet_data["salt"])
        nonce = bytes.fromhex(wallet_data["nonce"])
        ciphertext = bytes.fromhex(wallet_data["ciphertext"])
        address = wallet_data["address"]
        iterations = wallet_data.get("iterations", PBKDF2_ITERATIONS)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=iterations,
        )
        enc_key = kdf.derive(password.encode("utf-8"))

        aesgcm = AESGCM(enc_key)
        aad = address.encode("utf-8")

        try:
            plaintext = aesgcm.decrypt(nonce, ciphertext, aad)
        except Exception:
            raise ValueError("Неверный пароль или повреждённый файл кошелька")

        payload = json.loads(plaintext.decode("utf-8"))
        self._private_key = bytes.fromhex(payload["private_key"])
        self._address = address
        self._mnemonic = payload.get("mnemonic")

        acct = Account.from_key(self._private_key)
        if acct.address.lower() != address.lower():
            self.clear()
            raise ValueError("Ошибка целостности: адрес не совпадает с ключом")

        return self._address

    def get_private_key(self) -> bytes:
        """Возвращает приватный ключ (для подписи)."""
        if self._private_key is None:
            raise RuntimeError("Ключ не загружен")
        return self._private_key

    def clear(self) -> None:
        """Безопасная очистка ключей из памяти."""
        if self._private_key is not None:
            self._private_key = b'\x00' * 32
        self._private_key = None
        self._address = None
        self._mnemonic = None
