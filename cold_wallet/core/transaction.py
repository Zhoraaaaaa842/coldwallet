"""
ZhoraWallet ETH — Модуль подписи и сериализации транзакций.
Поддерживает Legacy и EIP-1559 транзакции.
Работает ОФЛАЙН — подписывает сырую транзакцию без обращения к сети.
"""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass

from eth_account import Account
from web3 import Web3


@dataclass
class TransactionRequest:
    """Параметры транзакции для подписи."""
    to: str
    value_wei: int
    nonce: int
    chain_id: int = 1
    gas_limit: int = 21000
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    gas_price: Optional[int] = None
    data: Optional[str] = None

    def validate(self) -> None:
        """Валидация параметров транзакции."""
        if not self.to or not Web3.is_address(self.to):
            raise ValueError(f"Невалидный адрес получателя: {self.to}")

        if self.value_wei < 0:
            raise ValueError("Сумма не может быть отрицательной")

        if self.nonce < 0:
            raise ValueError("Nonce не может быть отрицательным")

        if self.gas_limit < 21000:
            raise ValueError("Gas limit не может быть меньше 21000")

        has_eip1559 = (
            self.max_fee_per_gas is not None
            and self.max_priority_fee_per_gas is not None
        )
        has_legacy = self.gas_price is not None

        if not has_eip1559 and not has_legacy:
            raise ValueError(
                "Укажите max_fee_per_gas + max_priority_fee_per_gas (EIP-1559) "
                "или gas_price (Legacy)"
            )

        if has_eip1559 and has_legacy:
            raise ValueError(
                "Нельзя использовать одновременно EIP-1559 и Legacy параметры газа"
            )

        if has_eip1559 and self.max_priority_fee_per_gas > self.max_fee_per_gas:
            raise ValueError(
                "max_priority_fee_per_gas не может превышать max_fee_per_gas"
            )

        # FIX #4: валидация поля data — должно быть валидным hex
        if self.data is not None:
            d = self.data
            if d.startswith("0x") or d.startswith("0X"):
                d = d[2:]
            if d and not all(c in "0123456789abcdefABCDEF" for c in d):
                raise ValueError(
                    "Поле data должно быть hex-строкой (0x...). "
                    "Транзакция с невалидным data отклонена."
                )

    def to_dict(self) -> Dict[str, Any]:
        self.validate()

        tx: Dict[str, Any] = {
            "to": Web3.to_checksum_address(self.to),
            "value": self.value_wei,
            "nonce": self.nonce,
            "chainId": self.chain_id,
            "gas": self.gas_limit,
        }

        if self.max_fee_per_gas is not None:
            tx["maxFeePerGas"] = self.max_fee_per_gas
            tx["maxPriorityFeePerGas"] = self.max_priority_fee_per_gas
            tx["type"] = 2
        else:
            tx["gasPrice"] = self.gas_price

        if self.data:
            tx["data"] = self.data

        return tx


class TransactionSigner:
    """Подпись транзакций приватным ключом (офлайн)."""

    @staticmethod
    def sign_transaction(
        private_key: bytes,
        tx_request: TransactionRequest
    ) -> str:
        """Подписывает транзакцию и возвращает raw signed TX (hex)."""
        tx_dict = tx_request.to_dict()
        signed = Account.sign_transaction(tx_dict, private_key)
        return "0x" + signed.raw_transaction.hex()

    @staticmethod
    def sign_message(private_key: bytes, message: str) -> Dict[str, str]:
        """Подписывает произвольное сообщение (EIP-191)."""
        from eth_account.messages import encode_defunct
        msg = encode_defunct(text=message)
        signed = Account.sign_message(msg, private_key)
        return {
            "message": message,
            "signature": signed.signature.hex(),
            "v": str(signed.v),
            "r": hex(signed.r),
            "s": hex(signed.s),
        }

    @staticmethod
    def serialize_unsigned_tx(tx_request: TransactionRequest) -> str:
        """Сериализует неподписанную транзакцию в JSON для USB-передачи."""
        tx_request.validate()
        data = {
            "type": "unsigned_transaction",
            "version": 1,
            "tx": {
                "to": tx_request.to,
                "value_wei": str(tx_request.value_wei),
                "nonce": tx_request.nonce,
                "chain_id": tx_request.chain_id,
                "gas_limit": tx_request.gas_limit,
            }
        }

        if tx_request.max_fee_per_gas is not None:
            data["tx"]["max_fee_per_gas"] = str(tx_request.max_fee_per_gas)
            data["tx"]["max_priority_fee_per_gas"] = str(tx_request.max_priority_fee_per_gas)
            data["tx"]["tx_type"] = "eip1559"
        else:
            data["tx"]["gas_price"] = str(tx_request.gas_price)
            data["tx"]["tx_type"] = "legacy"

        if tx_request.data:
            data["tx"]["data"] = tx_request.data

        return json.dumps(data, indent=2)

    @staticmethod
    def deserialize_unsigned_tx(json_str: str) -> TransactionRequest:
        """Десериализация JSON → TransactionRequest."""
        data = json.loads(json_str)

        if data.get("type") != "unsigned_transaction":
            raise ValueError("Неверный формат: ожидается unsigned_transaction")

        tx = data["tx"]
        req = TransactionRequest(
            to=tx["to"],
            value_wei=int(tx["value_wei"]),
            nonce=tx["nonce"],
            chain_id=tx.get("chain_id", 1),
            gas_limit=tx.get("gas_limit", 21000),
        )

        if tx.get("tx_type") == "eip1559":
            req.max_fee_per_gas = int(tx["max_fee_per_gas"])
            req.max_priority_fee_per_gas = int(tx["max_priority_fee_per_gas"])
        else:
            gas_price_str = tx.get("gas_price")
            req.gas_price = int(gas_price_str) if gas_price_str is not None else None

        if "data" in tx:
            req.data = tx["data"]

        return req
