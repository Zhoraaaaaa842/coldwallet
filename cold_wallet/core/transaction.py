"""
ColdVault ETH — Модуль подписи и сериализации транзакций.
Поддерживает Legacy и EIP-1559 транзакции.
Работает ОФЛАЙН — подписывает сырую транзакцию без обращения к сети.
"""

import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3


@dataclass
class TransactionRequest:
    """Параметры транзакции для подписи."""
    to: str               # Адрес получателя
    value_wei: int        # Сумма в Wei
    nonce: int            # Nonce отправителя
    chain_id: int = 1     # 1 = Mainnet, 11155111 = Sepolia
    gas_limit: int = 21000
    # EIP-1559
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None
    # Legacy
    gas_price: Optional[int] = None
    # Data (для взаимодействия с контрактами)
    data: Optional[str] = None

    def validate(self) -> None:
        """Валидация параметров транзакции."""
        if not self.to or len(self.to) != 42 or not self.to.startswith("0x"):
            raise ValueError(f"Невалидный адрес получателя: {self.to}")

        if self.value_wei < 0:
            raise ValueError("Сумма не может быть отрицательной")

        if self.nonce < 0:
            raise ValueError("Nonce не может быть отрицательным")

        if self.gas_limit < 21000:
            raise ValueError("Gas limit не может быть меньше 21000")

        # Проверка: либо EIP-1559, либо Legacy
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

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для eth_account."""
        self.validate()

        tx: Dict[str, Any] = {
            "to": Web3.to_checksum_address(self.to),
            "value": self.value_wei,
            "nonce": self.nonce,
            "chainId": self.chain_id,
            "gas": self.gas_limit,
        }

        if self.max_fee_per_gas is not None:
            # EIP-1559 (Type 2)
            tx["maxFeePerGas"] = self.max_fee_per_gas
            tx["maxPriorityFeePerGas"] = self.max_priority_fee_per_gas
            tx["type"] = 2
        else:
            # Legacy
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
        """
        Подписывает транзакцию и возвращает raw signed TX (hex).
        
        Этот raw TX можно передать онлайн-ПК для broadcast.
        """
        tx_dict = tx_request.to_dict()
        signed = Account.sign_transaction(tx_dict, private_key)
        return signed.raw_transaction.hex()

    @staticmethod
    def sign_message(private_key: bytes, message: str) -> Dict[str, str]:
        """
        Подписывает произвольное сообщение (EIP-191).
        Возвращает словарь с компонентами подписи.
        """
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
        """
        Сериализует неподписанную транзакцию в JSON.
        Используется для передачи между онлайн-ПК и USB-кошельком.
        """
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
            data["tx"]["max_priority_fee_per_gas"] = str(
                tx_request.max_priority_fee_per_gas
            )
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
            req.gas_price = int(tx.get("gas_price", 0))

        if "data" in tx:
            req.data = tx["data"]

        return req
