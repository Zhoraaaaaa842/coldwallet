from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from web3 import Web3
from cold_wallet.core.transaction import TransactionRequest


@dataclass
class FeeOption:
    label: str
    max_fee_per_gas_wei: int
    max_priority_fee_wei: int
    gas_limit: int

    @property
    def max_fee_eth(self) -> str:
        return f"{Decimal(self.gas_limit * self.max_fee_per_gas_wei) / Decimal('1e18'):.8f}"

    @property
    def max_fee_gwei(self) -> str:
        return f"{Decimal(self.max_fee_per_gas_wei) / Decimal('1e9'):.4f}"

    @property
    def priority_gwei(self) -> str:
        return f"{Decimal(self.max_priority_fee_wei) / Decimal('1e9'):.4f}"


@dataclass
class FeeEstimate:
    base_fee_gwei: float
    gas_limit: int
    low: FeeOption
    medium: FeeOption
    high: FeeOption
    supports_eip1559: bool
    legacy_gas_price_wei: Optional[int] = None


class FeeEstimator:
    """
    Auto fee calculator for Ethereum EIP-1559 transactions.

    Usage:
        estimator = FeeEstimator(w3)
        estimate  = estimator.estimate_fee(from_addr, to_addr, value_eth=0.1)
        tx = estimator.build_transaction(from_addr, to_addr, 0.1, speed='medium', chain_id=1)
    """

    PRIORITY_FEES = {"low": 1.0, "medium": 1.5, "high": 3.0}
    LABELS = {"low": "Low", "medium": "Medium", "high": "High"}

    def __init__(self, w3: Web3) -> None:
        self._w3 = w3

    def estimate_fee(
        self,
        from_addr: str,
        to_addr: str,
        value_eth: float,
        data: str = "",
    ) -> FeeEstimate:
        value_wei = int(Decimal(str(value_eth)) * Decimal("1e18"))
        gas_limit = self._estimate_gas_limit(from_addr, to_addr, value_wei, data)

        try:
            block = self._w3.eth.get_block("latest")
            base_fee_wei: int = block.get("baseFeePerGas", 0)
            base_fee_gwei = base_fee_wei / 1e9
            supports_eip1559 = base_fee_wei > 0
        except Exception:
            base_fee_wei = 0
            base_fee_gwei = 0.0
            supports_eip1559 = False

        legacy: Optional[int] = None
        try:
            legacy = self._w3.eth.gas_price
        except Exception:
            pass

        def make(speed: str) -> FeeOption:
            p = int(self.PRIORITY_FEES[speed] * 1e9)
            # EIP-1559: maxFee = 2 * baseFee + priorityFee
            return FeeOption(self.LABELS[speed], int(2 * base_fee_wei + p), p, gas_limit)

        return FeeEstimate(
            base_fee_gwei=base_fee_gwei,
            gas_limit=gas_limit,
            low=make("low"),
            medium=make("medium"),
            high=make("high"),
            supports_eip1559=supports_eip1559,
            legacy_gas_price_wei=legacy,
        )

    def build_transaction(
        self,
        from_addr: str,
        to_addr: str,
        value_eth: float,
        speed: str = "medium",
        chain_id: int = 1,
        data: str = "",
        nonce: Optional[int] = None,
    ) -> TransactionRequest:
        if speed not in self.PRIORITY_FEES:
            raise ValueError(f"Invalid speed '{speed}'. Use: low, medium, high")

        if nonce is None:
            nonce = self._w3.eth.get_transaction_count(Web3.to_checksum_address(from_addr))

        est = self.estimate_fee(from_addr, to_addr, value_eth, data)
        opt = getattr(est, speed)
        value_wei = int(Decimal(str(value_eth)) * Decimal("1e18"))

        tx = TransactionRequest(
            to=to_addr,
            value_wei=value_wei,
            nonce=nonce,
            chain_id=chain_id,
            gas_limit=opt.gas_limit,
            max_fee_per_gas=opt.max_fee_per_gas_wei,
            max_priority_fee_per_gas=opt.max_priority_fee_wei,
        )
        if data:
            tx.data = data
        return tx

    def _estimate_gas_limit(self, from_addr: str, to_addr: str, value_wei: int, data: str) -> int:
        try:
            p = {
                "from": Web3.to_checksum_address(from_addr),
                "to": Web3.to_checksum_address(to_addr),
                "value": value_wei,
            }
            if data:
                p["data"] = data
            return int(self._w3.eth.estimate_gas(p) * 1.2)
        except Exception:
            return 21000

    @staticmethod
    def format_fee_summary(estimate: FeeEstimate, value_eth: float) -> str:
        lines = [
            f"Amount         : {value_eth} ETH",
            f"Gas limit      : {estimate.gas_limit:,}",
            f"Base fee       : {estimate.base_fee_gwei:.4f} Gwei",
            "-" * 52,
        ]
        for opt in (estimate.low, estimate.medium, estimate.high):
            lines.append(
                f"[{opt.label:<7}]  maxFee={opt.max_fee_gwei} Gwei"
                f"  tip={opt.priority_gwei} Gwei  ~{opt.max_fee_eth} ETH"
            )
        return "\n".join(lines)
