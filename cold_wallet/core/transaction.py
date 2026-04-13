"""
ZhoraWallet ETH — Python-обёртка над Rust TransactionSigner.

Если Rust-крейт собран — используем его.
Иначе — fallback на Python-реализацию через eth_account.
"""

try:
    from coldvault_core import (  # type: ignore
        TransactionRequest as _RustTransactionRequest,
        TransactionSigner as _RustTransactionSigner,
    )
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

import json as _json
from dataclasses import dataclass, field
from typing import Optional
from eth_account import Account
from eth_account.datastructures import SignedTransaction


def _to_hex(value: int) -> str:
    """
    Преобразует int в hex-строку для PyO3-полей U256/u64.
    Rust-обёртки (coldvault_core) принимают числовые поля как строки "0x...".
    """
    return hex(value)


@dataclass
class TransactionRequest:
    """Данные транзакции (Python fallback + совместимость с Rust)."""
    to: str
    value: int           # Wei
    gas_limit: int
    nonce: int
    chain_id: int
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    gas_price: Optional[int] = None
    data: bytes = field(default_factory=bytes)

    def __init__(self, to: str, value: int = 0, gas_limit: int = 21000,
                 nonce: int = 0, chain_id: int = 1,
                 max_fee_per_gas: Optional[int] = None,
                 max_priority_fee_per_gas: Optional[int] = None,
                 gas_price: Optional[int] = None,
                 data: bytes = b"",
                 value_wei: Optional[int] = None, **kwargs):
        self.to = to
        self.value = value_wei if value_wei is not None else value
        self.gas_limit = gas_limit
        self.nonce = nonce
        self.chain_id = chain_id
        self.max_fee_per_gas = max_fee_per_gas
        self.max_priority_fee_per_gas = max_priority_fee_per_gas
        self.gas_price = gas_price
        self.data = data if isinstance(data, bytes) else (data or b"")

    def tx_type(self) -> str:
        return "eip1559" if self.max_fee_per_gas is not None else "legacy"

    def to_rust(self):
        """
        Конвертирует в Rust TransactionRequest.
        PyO3-поля U256/u64 принимают числа как hex-строки "0x...".
        """
        if not _RUST_AVAILABLE:
            return self
        kwargs = {
            "to": self.to,
            "value": _to_hex(self.value),
            "gas_limit": _to_hex(self.gas_limit),
            "nonce": _to_hex(self.nonce),
            "chain_id": _to_hex(self.chain_id),
        }
        if self.max_fee_per_gas is not None:
            kwargs["max_fee_per_gas"] = _to_hex(self.max_fee_per_gas)
        if self.max_priority_fee_per_gas is not None:
            kwargs["max_priority_fee_per_gas"] = _to_hex(self.max_priority_fee_per_gas)
        if self.gas_price is not None:
            kwargs["gas_price"] = _to_hex(self.gas_price)
        if self.data:
            kwargs["data"] = self.data
        return _RustTransactionRequest(**kwargs)


class TransactionSigner:
    """Обёртка: использует Rust если доступен, иначе Python fallback."""

    def __init__(self, private_key: bytes):
        if len(private_key) != 32:
            raise ValueError("Приватный ключ должен быть 32 байта")
        self._private_key = private_key
        if _RUST_AVAILABLE:
            self._rust_signer = _RustTransactionSigner(private_key)
        else:
            self._rust_signer = None

    def sign_transaction(self, tx: TransactionRequest) -> str:
        if _RUST_AVAILABLE and self._rust_signer:
            rust_tx = tx.to_rust()
            return self._rust_signer.sign_transaction(rust_tx)
        # Python fallback
        from web3 import Web3
        acct = Account.from_key(self._private_key)
        to_addr = Web3.to_checksum_address(tx.to)
        if tx.tx_type() == "eip1559":
            tx_dict = {
                "type": "0x2",
                "to": to_addr,
                "value": tx.value,
                "gas": tx.gas_limit,
                "nonce": tx.nonce,
                "chainId": tx.chain_id,
                "maxFeePerGas": tx.max_fee_per_gas,
                "maxPriorityFeePerGas": tx.max_priority_fee_per_gas,
                "data": tx.data or b"",
            }
        else:
            tx_dict = {
                "to": to_addr,
                "value": tx.value,
                "gas": tx.gas_limit,
                "nonce": tx.nonce,
                "chainId": tx.chain_id,
                "gasPrice": tx.gas_price,
                "data": tx.data or b"",
            }
        signed: SignedTransaction = acct.sign_transaction(tx_dict)
        raw = getattr(signed, 'raw_transaction', None) or getattr(signed, 'rawTransaction')
        return raw.hex()

    def get_address(self) -> str:
        if _RUST_AVAILABLE and self._rust_signer:
            return self._rust_signer.get_address()
        return Account.from_key(self._private_key).address

    @staticmethod
    def serialize_unsigned_tx(tx: TransactionRequest) -> str:
        """Сериализует TransactionRequest в JSON для сохранения на USB."""
        tx_data = {
            "tx": {
                "to": tx.to,
                "value_wei": tx.value,
                "gas_limit": tx.gas_limit,
                "nonce": tx.nonce,
                "chain_id": tx.chain_id,
                "tx_type": tx.tx_type(),
            },
            "version": 1,
            "type": "unsigned_transaction",
        }
        if tx.tx_type() == "eip1559":
            tx_data["tx"]["max_fee_per_gas"] = tx.max_fee_per_gas
            tx_data["tx"]["max_priority_fee_per_gas"] = tx.max_priority_fee_per_gas
        else:
            tx_data["tx"]["gas_price"] = tx.gas_price
        if tx.data:
            tx_data["tx"]["data"] = tx.data.hex() if isinstance(tx.data, bytes) else tx.data
        return _json.dumps(tx_data, indent=2)

    @staticmethod
    def deserialize_unsigned_tx(tx_json: str) -> TransactionRequest:
        """Десериализует JSON с USB обратно в TransactionRequest."""
        data = _json.loads(tx_json) if isinstance(tx_json, str) else tx_json
        tx = data.get("tx", data)
        value = int(tx.get("value_wei", tx.get("value", 0)))

        kwargs = {
            "to": tx["to"],
            "value": value,
            "gas_limit": int(tx.get("gas_limit", 21000)),
            "nonce": int(tx.get("nonce", 0)),
            "chain_id": int(tx.get("chain_id", 1)),
        }
        if tx.get("tx_type") == "eip1559" or tx.get("max_fee_per_gas") is not None:
            kwargs["max_fee_per_gas"] = int(tx["max_fee_per_gas"])
            kwargs["max_priority_fee_per_gas"] = int(tx["max_priority_fee_per_gas"])
        else:
            kwargs["gas_price"] = int(tx.get("gas_price", 0))
        if tx.get("data"):
            d = tx["data"]
            kwargs["data"] = bytes.fromhex(d.replace("0x", "")) if isinstance(d, str) else d
        return TransactionRequest(**kwargs)
