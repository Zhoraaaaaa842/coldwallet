"""
ZhoraWallet ETH — Python-обёртка над Rust TransactionSigner.

Если Rust-крейт собран — используем его.
Иначе — fallback на Python-реализацию через eth_account.
"""

try:
    from coldvault_core import (  # type: ignore
        TransactionRequest,
        TransactionSigner,
    )
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

if not _RUST_AVAILABLE:
    # --- Fallback Python-реализация ---
    from dataclasses import dataclass, field
    from typing import Optional
    from eth_account import Account
    from eth_account.datastructures import SignedTransaction

    @dataclass
    class TransactionRequest:  # type: ignore[no-redef]
        """Данные транзакции (Python fallback)."""
        to: str
        value: int           # Wei
        gas_limit: int
        nonce: int
        chain_id: int
        max_fee_per_gas: Optional[int] = None
        max_priority_fee_per_gas: Optional[int] = None
        gas_price: Optional[int] = None
        data: bytes = field(default_factory=bytes)

        def tx_type(self) -> str:
            return "eip1559" if self.max_fee_per_gas is not None else "legacy"

    class TransactionSigner:  # type: ignore[no-redef]
        """Python fallback TransactionSigner."""

        def __init__(self, private_key: bytes):
            if len(private_key) != 32:
                raise ValueError("Приватный ключ должен быть 32 байта")
            self._private_key = private_key

        def sign_transaction(self, tx: TransactionRequest) -> str:
            acct = Account.from_key(self._private_key)
            if tx.tx_type() == "eip1559":
                tx_dict = {
                    "type": "0x2",
                    "to": tx.to,
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
                    "to": tx.to,
                    "value": tx.value,
                    "gas": tx.gas_limit,
                    "nonce": tx.nonce,
                    "chainId": tx.chain_id,
                    "gasPrice": tx.gas_price,
                    "data": tx.data or b"",
                }
            signed: SignedTransaction = acct.sign_transaction(tx_dict)
            return signed.rawTransaction.hex()

        def get_address(self) -> str:
            return Account.from_key(self._private_key).address
