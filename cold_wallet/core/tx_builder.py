from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from web3 import Web3
from cold_wallet.core.fee_estimator import FeeEstimate, FeeEstimator
from cold_wallet.core.transaction import TransactionRequest


@dataclass
class PreparedTransaction:
    """Result of TxBuilder.prepare() — ready for signing."""
    tx_request: TransactionRequest
    estimate: FeeEstimate
    fee_summary: str
    from_addr: str
    to_addr: str
    value_eth: float
    speed: str
    nonce: int


class TxBuilder:
    """
    High-level transaction builder with automatic fee calculation.

    Usage:
        builder = TxBuilder("https://eth.llamarpc.com")
        result  = builder.prepare(
            from_addr="0xYourAddress",
            to_addr="0xRecipient",
            value_eth=0.05,
            speed="medium",  # low | medium | high
        )
        print(result.fee_summary)          # show fee options to user
        tx = result.tx_request             # pass to TransactionSigner
    """

    def __init__(self, rpc_url: str) -> None:
        self._w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        if not self._w3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC: {rpc_url}")
        self._estimator = FeeEstimator(self._w3)

    def prepare(
        self,
        from_addr: str,
        to_addr: str,
        value_eth: float,
        speed: str = "medium",
        chain_id: int = 1,
        data: str = "",
        nonce: Optional[int] = None,
    ) -> PreparedTransaction:
        """
        Automatically:
          1. Fetches sender nonce from network
          2. Estimates gas limit (eth_estimateGas + 20% buffer)
          3. Fetches current base fee from latest block
          4. Calculates commission for chosen speed (low/medium/high)
          5. Returns TransactionRequest ready for signing

        Args:
            from_addr  - sender address (0x...)
            to_addr    - recipient address (0x...)
            value_eth  - amount to send in ETH (e.g. 0.05)
            speed      - fee speed: "low" | "medium" | "high"
            chain_id   - 1=mainnet, 11155111=sepolia
            data       - calldata for contracts (optional)
            nonce      - override nonce (auto-fetched if None)
        """
        if nonce is None:
            nonce = self._w3.eth.get_transaction_count(
                Web3.to_checksum_address(from_addr)
            )

        estimate = self._estimator.estimate_fee(from_addr, to_addr, value_eth, data)
        tx = self._estimator.build_transaction(
            from_addr=from_addr,
            to_addr=to_addr,
            value_eth=value_eth,
            speed=speed,
            chain_id=chain_id,
            data=data,
            nonce=nonce,
        )
        summary = FeeEstimator.format_fee_summary(estimate, value_eth)

        return PreparedTransaction(
            tx_request=tx,
            estimate=estimate,
            fee_summary=summary,
            from_addr=from_addr,
            to_addr=to_addr,
            value_eth=value_eth,
            speed=speed,
            nonce=nonce,
        )

    def get_fee_estimate(
        self,
        from_addr: str,
        to_addr: str,
        value_eth: float,
        data: str = "",
    ) -> FeeEstimate:
        """Only calculate fee estimate without building TransactionRequest."""
        return self._estimator.estimate_fee(from_addr, to_addr, value_eth, data)

    @property
    def chain_id(self) -> int:
        return self._w3.eth.chain_id

    @property
    def web3(self) -> Web3:
        return self._w3
