"""
ZhoraWallet ETH — Python-обёртка над Rust transaction модулем.
Вся логика подписи теперь в coldvault_core (Rust).

Импорт остался тем же:
    from cold_wallet.core.transaction import TransactionRequest, TransactionSigner
"""

from typing import Optional, Dict, Any

try:
    from coldvault_core import (
        TransactionRequest as _RustTransactionRequest,
        TransactionSigner as _RustTransactionSigner,
    )
    _RUST_AVAILABLE = True
except ImportError:
    _RUST_AVAILABLE = False

if not _RUST_AVAILABLE:
    import warnings
    warnings.warn(
        "coldvault_core (Rust) не найден. Используется Python fallback.",
        RuntimeWarning, stacklevel=2,
    )
    from cold_wallet.core._transaction_py import (  # type: ignore
        TransactionRequest, TransactionSigner
    )
else:
    class TransactionRequest(_RustTransactionRequest):  # type: ignore[misc]
        """
        Параметры ETH транзакции.

        Поля:
            to                    : str   — адрес получателя
            value_wei             : int   — сумма в wei
            nonce                 : int
            chain_id              : int   (default: 1 — Ethereum mainnet)
            gas_limit             : int   (default: 21000)
            max_fee_per_gas       : int | None  — EIP-1559
            max_priority_fee_per_gas: int | None  — EIP-1559
            gas_price             : int | None  — Legacy
            data                  : str | None  — hex данные контракта

        Пример (EIP-1559):
            tx = TransactionRequest(
                to="0xAbCd...",
                value_wei=10**18,
                nonce=5,
                chain_id=1,
                max_fee_per_gas=50_000_000_000,
                max_priority_fee_per_gas=2_000_000_000,
            )
        """
        pass

    class TransactionSigner(_RustTransactionSigner):  # type: ignore[misc]
        """
        Подпись ETH транзакций.

        Методы:
            sign_transaction(private_key: bytes, tx: TransactionRequest) -> str
                Возвращает 0x... raw signed TX hex.

            sign_message(private_key: bytes, message: str) -> dict
                EIP-191 подпись. Возвращает {message, signature, v, r, s}.
        """
        pass


__all__ = ["TransactionRequest", "TransactionSigner"]
