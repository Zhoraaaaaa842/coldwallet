"""
ColdVault ETH — Модуль работы с сетью Ethereum.
Используется ТОЛЬКО на онлайн-ПК (десктоп-приложение).
Запросы баланса, nonce, gas price, отправка signed TX.
"""

import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from decimal import Decimal

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware


# Публичные RPC-ноды (без API ключа)
RPC_ENDPOINTS = {
    "mainnet": [
        "https://eth.llamarpc.com",
        "https://rpc.ankr.com/eth",
        "https://ethereum-rpc.publicnode.com",
        "https://1rpc.io/eth",
    ],
    "sepolia": [
        "https://rpc.sepolia.org",
        "https://rpc.ankr.com/eth_sepolia",
        "https://ethereum-sepolia-rpc.publicnode.com",
    ],
}

CHAIN_IDS = {
    "mainnet": 1,
    "sepolia": 11155111,
}

# Etherscan-совместимые API для истории транзакций (без ключа, лимит 5 req/s)
ETHERSCAN_API = {
    "mainnet": "https://api.etherscan.io/api",
    "sepolia": "https://api-sepolia.etherscan.io/api",
}


class EthNetwork:
    """Взаимодействие с Ethereum через RPC."""

    def __init__(self, network: str = "mainnet", custom_rpc: Optional[str] = None):
        self._network = network
        self._w3: Optional[Web3] = None
        self._connected = False

        if custom_rpc:
            self._rpc_list = [custom_rpc]
        else:
            self._rpc_list = RPC_ENDPOINTS.get(network, RPC_ENDPOINTS["mainnet"])

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def network(self) -> str:
        return self._network

    @property
    def chain_id(self) -> int:
        return CHAIN_IDS.get(self._network, 1)

    def connect(self) -> bool:
        """
        Подключение к Ethereum RPC.
        Перебирает ноды до первой рабочей.
        """
        for rpc_url in self._rpc_list:
            try:
                w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
                # Для PoA сетей (Sepolia и др.)
                if self._network != "mainnet":
                    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

                if w3.is_connected():
                    self._w3 = w3
                    self._connected = True
                    return True
            except Exception:
                continue

        self._connected = False
        return False

    def disconnect(self) -> None:
        self._w3 = None
        self._connected = False

    def _require_connection(self) -> None:
        if not self._w3 or not self._connected:
            raise ConnectionError("Не подключен к сети Ethereum")

    def get_balance(self, address: str) -> Dict[str, str]:
        """
        Получает баланс адреса.
        Возвращает {"wei": "...", "eth": "...", "gwei": "..."}
        """
        self._require_connection()
        balance_wei = self._w3.eth.get_balance(
            Web3.to_checksum_address(address)
        )
        balance_eth = Decimal(str(balance_wei)) / Decimal("1000000000000000000")
        balance_gwei = Decimal(str(balance_wei)) / Decimal("1000000000")

        return {
            "wei": str(balance_wei),
            "eth": f"{balance_eth:.18f}".rstrip('0').rstrip('.'),
            "gwei": f"{balance_gwei:.9f}".rstrip('0').rstrip('.'),
        }

    def get_nonce(self, address: str) -> int:
        """Получает текущий nonce адреса."""
        self._require_connection()
        return self._w3.eth.get_transaction_count(
            Web3.to_checksum_address(address)
        )

    def get_gas_price(self) -> Dict[str, Any]:
        """
        Получает текущие цены газа.
        Для EIP-1559 возвращает base_fee + priority_fee.
        """
        self._require_connection()

        result: Dict[str, Any] = {}

        try:
            # EIP-1559
            latest_block = self._w3.eth.get_block("latest")
            base_fee = latest_block.get("baseFeePerGas", 0)
            result["base_fee_gwei"] = round(base_fee / 1e9, 4)
            result["base_fee_wei"] = base_fee

            # Рекомендации по priority fee
            result["priority_fee_low_gwei"] = 1.0
            result["priority_fee_medium_gwei"] = 1.5
            result["priority_fee_high_gwei"] = 3.0

            # max_fee = 2 * base_fee + priority_fee
            result["max_fee_low_gwei"] = round(2 * result["base_fee_gwei"] + 1.0, 4)
            result["max_fee_medium_gwei"] = round(2 * result["base_fee_gwei"] + 1.5, 4)
            result["max_fee_high_gwei"] = round(2 * result["base_fee_gwei"] + 3.0, 4)

            result["supports_eip1559"] = True
        except Exception:
            result["supports_eip1559"] = False

        # Legacy gas price как fallback
        try:
            gas_price = self._w3.eth.gas_price
            result["legacy_gas_price_gwei"] = round(gas_price / 1e9, 4)
            result["legacy_gas_price_wei"] = gas_price
        except Exception:
            pass

        return result

    def broadcast_transaction(self, raw_tx_hex: str) -> Dict[str, Any]:
        """
        Отправляет подписанную транзакцию в сеть.
        Ждёт receipt и возвращает реальный статус:
          - status: 1 = успех, 0 = revert, None = таймаут/ошибка
          - tx_hash: хэш транзакции
          - block: номер блока (если подтверждена)
          - gas_used: использованный газ
          - error: описание ошибки (если есть)
        """
        self._require_connection()

        if not raw_tx_hex.startswith("0x"):
            raw_tx_hex = "0x" + raw_tx_hex

        tx_hash = self._w3.eth.send_raw_transaction(bytes.fromhex(raw_tx_hex[2:]))
        tx_hash_hex = tx_hash.hex()

        try:
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return {
                "tx_hash": tx_hash_hex,
                "status": receipt["status"],   # 1 = успех, 0 = revert
                "block": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
                "error": None,
            }
        except Exception as e:
            # TX попала в mempool, но подтверждения не было в течение 120 сек
            return {
                "tx_hash": tx_hash_hex,
                "status": None,
                "block": None,
                "gas_used": None,
                "error": str(e),
            }

    def get_transaction_history(self, address: str, limit: int = 50) -> List[Dict]:
        """
        FIX #4: Реализация получения истории транзакций.
        Использует Etherscan-совместимый публичный API (без ключа).
        Возвращает список транзакций в виде dicts.
        """
        base_url = ETHERSCAN_API.get(self._network, ETHERSCAN_API["mainnet"])
        params = urllib.parse.urlencode({
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": limit,
            "sort": "desc",
            "apikey": "YourApiKeyToken",  # без ключа работает с лимитом
        })
        url = f"{base_url}?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ZhoraWallet/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data.get("status") == "1":
                return data.get("result", [])
            # status "0" может означать "нет транзакций" — не ошибка
            return []
        except Exception:
            return []

    def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Получает receipt транзакции (или None если pending)."""
        self._require_connection()
        try:
            receipt = self._w3.eth.get_transaction_receipt(tx_hash)
            return dict(receipt) if receipt else None
        except Exception:
            return None

    def wait_for_receipt(self, tx_hash: str, timeout: int = 120) -> Dict:
        """Ожидает подтверждения транзакции."""
        self._require_connection()
        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        return dict(receipt)

    def estimate_gas(self, from_addr: str, to_addr: str, value_wei: int, data: str = "") -> int:
        """Оценка газа для транзакции."""
        self._require_connection()
        tx = {
            "from": Web3.to_checksum_address(from_addr),
            "to": Web3.to_checksum_address(to_addr),
            "value": value_wei,
        }
        if data:
            tx["data"] = data
        return self._w3.eth.estimate_gas(tx)

    @staticmethod
    def is_valid_address(address: str) -> bool:
        """FIX #8: Проверка валидности Ethereum-адреса через web3."""
        return Web3.is_address(address)

    @staticmethod
    def wei_to_eth(wei: int) -> str:
        eth = Decimal(str(wei)) / Decimal("1000000000000000000")
        return f"{eth:.18f}".rstrip('0').rstrip('.')

    @staticmethod
    def eth_to_wei(eth: float) -> int:
        """FIX #7: Используем Decimal для точного перевода ETH → Wei."""
        return int(Decimal(str(eth)) * Decimal("1000000000000000000"))

    @staticmethod
    def gwei_to_wei(gwei: float) -> int:
        return int(Decimal(str(gwei)) * Decimal("1000000000"))
