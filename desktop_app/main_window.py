"""
ZhoraWallet ETH — Главное окно десктоп-приложения.
Редизайн под мобильный макет: история транзакций, фильтры, кнопка Etherscan.
"""

import os
import sys
import json
import time
import webbrowser
import traceback
import datetime
from collections import defaultdict
from pathlib import Path
from typing import Optional

try:
    import urllib.request as _urllib_req
except ImportError:
    _urllib_req = None

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QLineEdit, QFrame, QMessageBox, QFileDialog,
    QComboBox, QDoubleSpinBox, QTextEdit, QSpacerItem, QSizePolicy,
    QApplication, QProgressBar, QGroupBox, QGridLayout, QScrollArea,
    QInputDialog, QButtonGroup, QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QClipboard, QPixmap, QImage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cold_wallet.core.key_manager import KeyManager
from cold_wallet.core.transaction import TransactionSigner, TransactionRequest
from cold_wallet.core.eth_network import EthNetwork
from cold_wallet.core.qr_receiver import (
    generate_receive_qr, parse_qr_uri, decode_qr_from_image,
    HAS_QRCODE, HAS_PIL, HAS_CV2
)
from cold_wallet.storage.usb_manager import USBManager
from desktop_app.styles import (
    MAIN_STYLESHEET, COLORS, CARD_BALANCE_STYLE, ETH_ICON_STYLE
)


# ─── Поток получения цены ETH в рублях (CoinGecko) ─── #

class PriceWorker(QThread):
    price_ready = pyqtSignal(float)  # цена 1 ETH в RUB
    error = pyqtSignal(str)

    COINGECKO_URL = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=ethereum&vs_currencies=rub"
    )

    def run(self):
        try:
            if _urllib_req is None:
                self.error.emit("urllib недоступен")
                return
            req = _urllib_req.Request(
                self.COINGECKO_URL,
                headers={"User-Agent": "ZhoraWallet/1.0"},
            )
            with _urllib_req.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            price = float(data["ethereum"]["rub"])
            self.price_ready.emit(price)
        except Exception as e:
            self.error.emit(str(e))


# ─── Фоновые потоки ─── #

class NetworkWorker(QThread):
    balance_ready = pyqtSignal(dict)
    gas_ready = pyqtSignal(dict)
    nonce_ready = pyqtSignal(int)
    tx_sent = pyqtSignal(str)
    tx_history_ready = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, eth_net: EthNetwork):
        super().__init__()
        self._eth = eth_net
        self._task = None
        self._params = {}

    def fetch_balance(self, address: str):
        self._task = "balance"
        self._params = {"address": address}
        if not self.isRunning():
            self.start()

    def fetch_gas(self):
        self._task = "gas"
        if not self.isRunning():
            self.start()

    def fetch_nonce(self, address: str):
        self._task = "nonce"
        self._params = {"address": address}
        if not self.isRunning():
            self.start()

    def send_tx(self, raw_tx: str):
        self._task = "send_tx"
        self._params = {"raw_tx": raw_tx}
        if not self.isRunning():
            self.start()

    def fetch_tx_history(self, address: str):
        self._task = "tx_history"
        self._params = {"address": address}
        if not self.isRunning():
            self.start()

    def run(self):
        try:
            if self._task == "balance":
                result = self._eth.get_balance(self._params["address"])
                self.balance_ready.emit(result)
            elif self._task == "gas":
                result = self._eth.get_gas_price()
                self.gas_ready.emit(result)
            elif self._task == "nonce":
                result = self._eth.get_nonce(self._params["address"])
                self.nonce_ready.emit(result)
            elif self._task == "send_tx":
                tx_hash = self._eth.broadcast_transaction(self._params["raw_tx"])
                self.tx_sent.emit(tx_hash)
            elif self._task == "tx_history":
                try:
                    txs = self._eth.get_transaction_history(self._params["address"])
                    self.tx_history_ready.emit(txs)
                except Exception:
                    self.tx_history_ready.emit([])
        except Exception as e:
            self.error.emit(str(e))


# ─── Виджет одной транзакции (редизайн) ─── #

class TxItemWidget(QFrame):
    def __init__(self, tx: dict, my_address: str, eth_price_rub: float = 0.0, parent=None):
        super().__init__(parent)
        self.tx = tx
        self.setObjectName("txCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._hash = tx.get("hash", "")
        my_addr_lower = (my_address or "").lower()
        from_addr = tx.get("from", "").lower()
        is_incoming = from_addr != my_addr_lower
        self.tx_type = "in" if is_incoming else "out"

        # Цвета
        icon_color = COLORS["success"] if is_incoming else COLORS["error"]
        icon_bg = "rgba(34,197,94,0.12)" if is_incoming else "rgba(239,68,68,0.12)"
        arrow = "↓" if is_incoming else "↑"
        type_text = "Перевод"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Иконка-стрелка
        icon_lbl = QLabel(arrow)
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"color: {icon_color}; background: {icon_bg}; border-radius: 20px;"
            f" font-size: 17px; font-weight: 800;"
        )
        layout.addWidget(icon_lbl)

        # Центральный блок: тип + адрес + время
        info = QVBoxLayout()
        info.setSpacing(3)

        type_lbl = QLabel(type_text)
        type_lbl.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 600;"
        )
        info.addWidget(type_lbl)

        peer = tx.get("from", "") if is_incoming else tx.get("to", "")
        prefix = "от: " if is_incoming else "на: "
        if peer and len(peer) > 20:
            peer_short = peer[:10] + "…" + peer[-8:]
        else:
            peer_short = peer or "—"
        addr_lbl = QLabel(prefix + peer_short)
        addr_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px;"
            f" font-family: Consolas, monospace;"
        )
        info.addWidget(addr_lbl)

        ts = tx.get("timeStamp") or tx.get("timestamp")
        if ts:
            dt = datetime.datetime.fromtimestamp(int(ts))
            time_str = dt.strftime("%H:%M")
        else:
            time_str = tx.get("date", "")
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        info.addWidget(time_lbl)
        layout.addLayout(info, 1)

        # Правый блок: сумма ETH + сумма RUB + статус
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setSpacing(2)

        value_wei = int(tx.get("value", 0))
        value_eth = value_wei / 10**18
        sign = "+" if is_incoming else "−"
        amount_lbl = QLabel(f"{sign}{value_eth:.6f} ETH")
        amount_lbl.setStyleSheet(
            f"color: {icon_color}; font-size: 14px; font-weight: 700;"
        )
        amount_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(amount_lbl)

        # Конвертация в рубли
        if eth_price_rub > 0 and value_eth > 0:
            rub_val = value_eth * eth_price_rub
            rub_lbl = QLabel(f"≈ {rub_val:,.2f} ₽".replace(",", " "))
            rub_lbl.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 500;"
            )
            rub_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
            right.addWidget(rub_lbl)

        # Подтверждение
        status_row = QHBoxLayout()
        status_row.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_row.setSpacing(4)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 7px;")
        status_row.addWidget(dot)
        conf_lbl = QLabel("Подтверждено")
        conf_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        status_row.addWidget(conf_lbl)
        right.addLayout(status_row)

        layout.addLayout(right)

        # Hover-эффект через стиль
        self._base_style = (
            f"QFrame#txCard {{"
            f"  background: {COLORS['bg_secondary']};"
            f"  border: 1px solid {COLORS['border']};"
            f"  border-radius: 14px;"
            f"}}"
        )
        self._hover_style = (
            f"QFrame#txCard {{"
            f"  background: {COLORS['bg_hover']};"
            f"  border: 1px solid {COLORS.get('border_focus', COLORS['accent'])};"
            f"  border-radius: 14px;"
            f"}}"
        )
        self.setStyleSheet(self._base_style)

    def enterEvent(self, event):
        self.setStyleSheet(self._hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet(self._base_style)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if self._hash:
            webbrowser.open(f"https://etherscan.io/tx/{self._hash}")
        super().mousePressEvent(event)


# ─── Главное окно ─── #

class ColdVaultMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZhoraWallet")
        self.setMinimumSize(1100, 720)
        self.resize(1200, 800)

        self._km = KeyManager()
        self._usb = USBManager()
        self._eth = EthNetwork("mainnet")
        self._balance_worker = NetworkWorker(self._eth)
        self._nonce_worker = NetworkWorker(self._eth)
        self._gas_worker = NetworkWorker(self._eth)
        self._tx_worker = NetworkWorker(self._eth)
        self._history_worker = NetworkWorker(self._eth)
        self._price_worker = PriceWorker()
        self._price_worker.price_ready.connect(self._on_price_ready)
        self._price_worker.error.connect(lambda e: None)

        self._address: Optional[str] = None
        self._balance_eth = "0"
        self._eth_price_rub: float = 0.0
        self._current_nonce = 0
        self._usb_connected = False
        self._usb_display = None
        self._nonce_display = None
        self._net_display = None
        self._gas_display = None
        self._all_txs: list = []
        self._tx_filter = "all"

        self.setStyleSheet(MAIN_STYLESHEET)
        self._build_ui()
        self._connect_signals()

        QTimer.singleShot(500, self._detect_usb)
        QTimer.singleShot(1000, self._fetch_eth_price)
        self._price_timer = QTimer(self)
        self._price_timer.setInterval(180_000)
        self._price_timer.timeout.connect(self._fetch_eth_price)
        self._price_timer.start()

    def _fetch_eth_price(self):
        if not self._price_worker.isRunning():
            self._price_worker.start()

    def _on_price_ready(self, price_rub: float):
        self._eth_price_rub = price_rub
        self._update_balance_display()
        if hasattr(self, "_market_price_label"):
            self._market_price_label.setText(
                f"{price_rub:,.2f} ₽".replace(",", " ")
            )

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_dashboard_page())   # 0
        self._stack.addWidget(self._build_send_page())         # 1
        self._stack.addWidget(self._build_receive_page())      # 2
        self._stack.addWidget(self._build_sign_page())         # 3
        self._stack.addWidget(self._build_settings_page())     # 4
        main_layout.addWidget(self._stack, 1)

    # ─── Sidebar ─── #

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        logo = QLabel("◈ ZhoraWallet")
        logo.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 22px; font-weight: 700;"
            f" padding: 10px 8px 20px;"
        )
        layout.addWidget(logo)

        self._usb_status = QLabel("● USB отключён")
        self._usb_status.setStyleSheet(
            f"color: {COLORS['error']}; font-size: 12px; padding: 4px 8px 16px;"
        )
        layout.addWidget(self._usb_status)

        nav_items = [
            ("⌂  Кошелёк", 0),
            ("↗  Отправить", 1),
            ("▤  Получить (QR)", 2),
            ("✎  Подписать & Отправить", 3),
            ("⚙  Настройки", 4),
        ]

        self._nav_buttons = []
        for text, page_idx in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("sidebarBtn")
            btn.setCheckable(True)
            btn.setChecked(page_idx == 0)
            btn.clicked.connect(lambda checked, idx=page_idx: self._switch_page(idx))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()

        self._network_label = QLabel("Ethereum Mainnet")
        self._network_label.setObjectName("networkLabel")
        self._network_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._network_label)

        ver = QLabel("v1.0.0")
        ver.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding: 8px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        return sidebar

    # ─── Dashboard ─── #

    def _build_dashboard_page(self) -> QWidget:
        wrapper = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(wrapper)
        scroll.setObjectName("dashScroll")

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(18)

        header = QHBoxLayout()
        title = QLabel("Кошелёк")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        subtitle = QLabel("Ethereum · Основная сеть")
        subtitle.setObjectName("subtitleLabel")
        header.addWidget(subtitle)
        layout.addLayout(header)

        balance_card = QFrame()
        balance_card.setStyleSheet(CARD_BALANCE_STYLE)
        bc_layout = QVBoxLayout(balance_card)
        bc_layout.setSpacing(4)
        bc_layout.setContentsMargins(28, 24, 28, 24)

        top_row = QHBoxLayout()
        eth_icon = QLabel("Ξ Ethereum")
        eth_icon.setStyleSheet(ETH_ICON_STYLE)
        top_row.addWidget(eth_icon)
        top_row.addStretch()
        net_badge = QLabel("Основная сеть")
        net_badge.setStyleSheet(
            f"color: {COLORS['eth_blue']}; font-size: 12px; font-weight: 600;"
            f" background: rgba(98,126,234,0.15); border-radius: 6px; padding: 3px 10px;"
        )
        top_row.addWidget(net_badge)
        bc_layout.addLayout(top_row)

        bal_title = QLabel("Баланс")
        bal_title.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 14px; font-weight: 600;"
            f" letter-spacing: 0.5px; margin-top: 12px;"
        )
        bc_layout.addWidget(bal_title)

        self._balance_rub_label = QLabel("— ₽")
        self._balance_rub_label.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 46px; font-weight: 800;"
            f" letter-spacing: -1px; line-height: 1;"
        )
        bc_layout.addWidget(self._balance_rub_label)

        self._balance_label = QLabel("—")
        self._balance_label.setObjectName("balanceLabel")
        self._balance_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 16px; font-weight: 500;"
            f" margin-top: 2px;"
        )
        bc_layout.addWidget(self._balance_label)

        self._market_price_label = QLabel("Загрузка курса…")
        self._market_price_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; margin-top: 6px;"
        )
        bc_layout.addWidget(self._market_price_label)

        self._address_label = QLabel("Подключите USB для начала работы")
        self._address_label.setObjectName("addressLabel")
        self._address_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._address_label.setToolTip("Нажмите для копирования")
        self._address_label.mousePressEvent = self._copy_address
        self._address_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
            f" font-family: Consolas, monospace; margin-top: 8px;"
        )
        bc_layout.addWidget(self._address_label)

        layout.addWidget(balance_card)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        btn_recv = QPushButton("↓  Получить")
        btn_recv.setObjectName("primaryBtn")
        btn_recv.clicked.connect(lambda: self._switch_page(2))
        actions_layout.addWidget(btn_recv)

        btn_send = QPushButton("↑  Отправить")
        btn_send.setObjectName("primaryBtn")
        btn_send.clicked.connect(lambda: self._switch_page(1))
        actions_layout.addWidget(btn_send)

        self._btn_refresh = QPushButton("⟳  Обновить")
        self._btn_refresh.setObjectName("secondaryBtn")
        self._btn_refresh.setEnabled(False)
        self._btn_refresh.clicked.connect(self._refresh_balance)
        actions_layout.addWidget(self._btn_refresh)

        btn_copy = QPushButton("⎘  Копировать")
        btn_copy.setObjectName("secondaryBtn")
        btn_copy.clicked.connect(lambda: self._copy_address(None))
        actions_layout.addWidget(btn_copy)

        layout.addLayout(actions_layout)

        self._btn_etherscan = QPushButton("⧉  Открыть в обозревателе блокчейна (Etherscan)")
        self._btn_etherscan.setObjectName("etherscanBtn")
        self._btn_etherscan.setMinimumHeight(44)
        self._btn_etherscan.setStyleSheet(
            f"QPushButton {{"
            f"  color: {COLORS['eth_blue']};"
            f"  background: rgba(98,126,234,0.10);"
            f"  border: 1.5px solid rgba(98,126,234,0.45);"
            f"  border-radius: 12px;"
            f"  padding: 10px 20px;"
            f"  font-size: 14px;"
            f"  font-weight: 600;"
            f"  text-align: left;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: rgba(98,126,234,0.20);"
            f"  border-color: {COLORS['eth_blue']};"
            f"}}"
            f"QPushButton:pressed {{"
            f"  background: rgba(98,126,234,0.28);"
            f"}}"
        )
        self._btn_etherscan.clicked.connect(self._open_etherscan)
        layout.addWidget(self._btn_etherscan)

        info_grid = QGridLayout()
        info_grid.setSpacing(12)

        nonce_card = self._make_info_card("Nonce", "—")
        self._nonce_display = nonce_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(nonce_card, 0, 0)

        net_card = self._make_info_card("Сеть", "Mainnet")
        self._net_display = net_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(net_card, 0, 1)

        gas_card = self._make_info_card("Gas Price", "—")
        self._gas_display = gas_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(gas_card, 0, 2)

        usb_info_card = self._make_info_card("USB", "Не подкл.")
        self._usb_display = usb_info_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(usb_info_card, 0, 3)

        layout.addLayout(info_grid)

        tx_header = QHBoxLayout()
        tx_title = QLabel("История транзакций")
        tx_title.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: 700;"
        )
        tx_header.addWidget(tx_title)
        tx_header.addStretch()

        btn_open_explorer = QPushButton("Обозреватель →")
        btn_open_explorer.setStyleSheet(
            f"color: {COLORS['accent']}; background: transparent; border: none;"
            f" font-size: 13px; font-weight: 600; padding: 0;"
        )
        btn_open_explorer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_explorer.clicked.connect(self._open_etherscan)
        tx_header.addWidget(btn_open_explorer)
        layout.addLayout(tx_header)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self._chip_all = self._make_chip("Все", True)
        self._chip_in = self._make_chip("Входящие", False)
        self._chip_out = self._make_chip("Исходящие", False)

        self._chip_all.clicked.connect(lambda: self._filter_txs("all"))
        self._chip_in.clicked.connect(lambda: self._filter_txs("in"))
        self._chip_out.clicked.connect(lambda: self._filter_txs("out"))

        filter_row.addWidget(self._chip_all)
        filter_row.addWidget(self._chip_in)
        filter_row.addWidget(self._chip_out)
        filter_row.addStretch()

        self._btn_refresh_txs = QPushButton("⟳")
        self._btn_refresh_txs.setObjectName("secondaryBtn")
        self._btn_refresh_txs.setFixedSize(38, 34)
        self._btn_refresh_txs.setToolTip("Обновить историю транзакций")
        self._btn_refresh_txs.clicked.connect(self._load_tx_history)
        filter_row.addWidget(self._btn_refresh_txs)

        layout.addLayout(filter_row)

        self._tx_container = QVBoxLayout()
        self._tx_container.setSpacing(8)

        self._tx_empty_lbl = QLabel("Нет транзакций. Подключите USB и обновите баланс.")
        self._tx_empty_lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 13px; padding: 32px 0;"
        )
        self._tx_empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tx_container.addWidget(self._tx_empty_lbl)

        layout.addLayout(self._tx_container)
        layout.addStretch()

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)
        return outer

    # ─── Обновление баланса ─── #

    def _update_balance_display(self):
        eth_str = self._balance_eth
        try:
            eth_val = float(eth_str)
        except (ValueError, TypeError):
            eth_val = 0.0

        self._balance_label.setText(f"{eth_val:.8f} ETH")

        if self._eth_price_rub > 0:
            rub_val = eth_val * self._eth_price_rub
            rub_int = int(rub_val)
            rub_dec = round((rub_val - rub_int) * 100)
            rub_int_fmt = f"{rub_int:,}".replace(",", " ")
            self._balance_rub_label.setText(f"{rub_int_fmt},{rub_dec:02d} ₽")

            price_fmt = f"{self._eth_price_rub:,.0f}".replace(",", " ")
            self._market_price_label.setText(
                f"Рыночная цена ETH · {price_fmt} ₽"
            )
        else:
            self._balance_rub_label.setText("— ₽")
            self._market_price_label.setText("Загрузка курса…")

    # ─── Чип-фильтр ─── #

    def _make_chip(self, text: str, active: bool) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        active_style = (
            f"background: rgba(168,85,247,0.15); border: 1.5px solid rgba(168,85,247,0.5);"
            f" color: {COLORS['accent']}; border-radius: 16px; padding: 5px 18px;"
            f" font-size: 13px; font-weight: 600;"
        )
        inactive_style = (
            f"background: {COLORS['bg_secondary']}; border: 1px solid {COLORS['border']};"
            f" color: {COLORS['text_muted']}; border-radius: 16px; padding: 5px 18px;"
            f" font-size: 13px; font-weight: 500;"
        )
        btn.setStyleSheet(active_style if active else inactive_style)
        btn._active_style = active_style
        btn._inactive_style = inactive_style
        return btn

    def _filter_txs(self, f: str):
        self._tx_filter = f
        for chip, name in [
            (self._chip_all, "all"),
            (self._chip_in, "in"),
            (self._chip_out, "out"),
        ]:
            is_active = name == f
            chip.setChecked(is_active)
            chip.setStyleSheet(chip._active_style if is_active else chip._inactive_style)
        self._render_tx_list(self._all_txs)

    # ─── Рендер транзакций ─── #

    def _render_tx_list(self, txs: list):
        while self._tx_container.count():
            item = self._tx_container.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        my = (self._address or "").lower()
        filtered = []
        for tx in txs:
            is_in = tx.get("from", "").lower() != my
            if self._tx_filter == "all":
                filtered.append(tx)
            elif self._tx_filter == "in" and is_in:
                filtered.append(tx)
            elif self._tx_filter == "out" and not is_in:
                filtered.append(tx)

        if not filtered:
            lbl = QLabel(
                "Транзакций не найдено."
                if txs else
                "Нет транзакций. Подключите USB и обновите баланс."
            )
            lbl.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 13px; padding: 32px 0;"
            )
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._tx_container.addWidget(lbl)
            return

        groups = defaultdict(list)
        today_str = datetime.date.today().strftime("%d.%m.%Y")
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d.%m.%Y")

        for tx in filtered:
            ts = tx.get("timeStamp") or tx.get("timestamp")
            if ts:
                d = datetime.datetime.fromtimestamp(int(ts)).strftime("%d.%m.%Y")
                if d == today_str:
                    label = "Сегодня"
                elif d == yesterday:
                    label = "Вчера"
                else:
                    label = d
            else:
                label = tx.get("date", "Неизвестно")
            groups[label].append(tx)

        for date_label, group in groups.items():
            sep = QLabel(date_label.upper())
            sep.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 700;"
                f" padding: 10px 0 4px; letter-spacing: 0.8px;"
            )
            self._tx_container.addWidget(sep)
            for tx in group:
                item = TxItemWidget(tx, self._address or "", self._eth_price_rub)
                self._tx_container.addWidget(item)

    def _load_tx_history(self):
        if not self._address:
            return
        self._history_worker._eth = self._eth
        self._history_worker.tx_history_ready.connect(self._on_tx_history_received)
        self._history_worker.fetch_tx_history(self._address)

    def _on_tx_history_received(self, txs: list):
        self._all_txs = txs
        self._render_tx_list(txs)

    def _open_etherscan(self):
        if self._address:
            webbrowser.open(f"https://etherscan.io/address/{self._address}")
        else:
            webbrowser.open("https://etherscan.io")

    def _copy_address(self, event=None):
        if self._address:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._address)
            self._address_label.setText(
                self._address[:10] + "…" + self._address[-8:] + "  ✓ Скопировано"
            )
            QTimer.singleShot(2000, self._restore_address_label)
        else:
            QMessageBox.information(self, "Нет адреса", "Кошелёк не разблокирован.")

    def _restore_address_label(self):
        if self._address:
            short = self._address[:10] + "…" + self._address[-8:]
            self._address_label.setText(short)

    def _make_info_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)
        card_layout.setContentsMargins(16, 14, 16, 14)

        t = QLabel(title)
        t.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px;"
            f" font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;"
        )
        card_layout.addWidget(t)

        v = QLabel(value)
        v.setObjectName("infoValue")
        v.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: 700;"
        )
        card_layout.addWidget(v)

        return card

    # ─── Receive page ─── #

    def _build_receive_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Получить ETH")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Покажите QR отправителю — или сканируйте входящий QR для заполнения формы отправки")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        content = QHBoxLayout()
        content.setSpacing(20)

        gen_card = QFrame()
        gen_card.setObjectName("card")
        gen_layout = QVBoxLayout(gen_card)
        gen_layout.setSpacing(12)

        gen_title = QLabel("Генерация QR для получения")
        gen_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 16px;")
        gen_layout.addWidget(gen_title)

        self._qr_image_label = QLabel()
        self._qr_image_label.setFixedSize(250, 250)
        self._qr_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_image_label.setStyleSheet(
            f"background: white; border-radius: 8px; border: 1px solid {COLORS.get('border', '#333')};"
        )
        self._qr_image_label.setText("Подключите\nUSB")
        gen_layout.addWidget(self._qr_image_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        gen_layout.addWidget(self._make_field_label("Сумма ETH (опционально)"))
        self._qr_amount_input = QDoubleSpinBox()
        self._qr_amount_input.setDecimals(8)
        self._qr_amount_input.setMaximum(1_000_000)
        self._qr_amount_input.setSpecialValueText("Любая сумма")
        gen_layout.addWidget(self._qr_amount_input)

        btn_gen = QPushButton("⎙ Сгенерировать QR")
        btn_gen.setObjectName("primaryBtn")
        btn_gen.clicked.connect(self._generate_qr)
        gen_layout.addWidget(btn_gen)

        btn_save_qr = QPushButton("↓ Сохранить QR в PNG")
        btn_save_qr.setObjectName("secondaryBtn")
        btn_save_qr.clicked.connect(self._save_qr_image)
        gen_layout.addWidget(btn_save_qr)

        gen_layout.addStretch()
        content.addWidget(gen_card, 1)

        scan_card = QFrame()
        scan_card.setObjectName("card")
        scan_layout = QVBoxLayout(scan_card)
        scan_layout.setSpacing(12)

        scan_title = QLabel("Сканировать входящий QR")
        scan_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 16px;")
        scan_layout.addWidget(scan_title)

        scan_hint = QLabel(
            "Загрузите PNG/JPG изображение QR или введите URI вручную.\n"
            "Форматы: ethereum:0x... или голый 0x-адрес"
        )
        scan_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        scan_hint.setWordWrap(True)
        scan_layout.addWidget(scan_hint)

        btn_scan_file = QPushButton("📁 Загрузить изображение QR")
        btn_scan_file.setObjectName("secondaryBtn")
        btn_scan_file.clicked.connect(self._scan_qr_from_file)
        scan_layout.addWidget(btn_scan_file)

        scan_layout.addWidget(self._make_field_label("или введите URI вручную:"))
        self._qr_uri_input = QLineEdit()
        self._qr_uri_input.setPlaceholderText("ethereum:0x... или 0x...")
        scan_layout.addWidget(self._qr_uri_input)

        btn_parse = QPushButton("▶ Разобрать URI")
        btn_parse.setObjectName("primaryBtn")
        btn_parse.clicked.connect(self._parse_qr_uri)
        scan_layout.addWidget(btn_parse)

        result_card = QFrame()
        result_card.setObjectName("card")
        result_layout = QVBoxLayout(result_card)

        res_hdr = QLabel("Результат:")
        res_hdr.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
        result_layout.addWidget(res_hdr)

        self._qr_result_addr = QLabel("—")
        self._qr_result_addr.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: 700;")
        self._qr_result_addr.setWordWrap(True)
        result_layout.addWidget(self._qr_result_addr)

        self._qr_result_amount = QLabel("")
        self._qr_result_amount.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px;")
        result_layout.addWidget(self._qr_result_amount)

        btn_fill_send = QPushButton("↗ Заполнить форму Отправки")
        btn_fill_send.setObjectName("primaryBtn")
        btn_fill_send.clicked.connect(self._fill_send_from_qr)
        result_layout.addWidget(btn_fill_send)

        scan_layout.addWidget(result_card)
        scan_layout.addStretch()
        content.addWidget(scan_card, 1)

        layout.addLayout(content)
        layout.addStretch()

        self._last_qr_request = None
        self._qr_pil_image = None

        return page

    # ─── QR логика ─── #

    def _generate_qr(self):
        if not self._address:
            QMessageBox.warning(self, "Ошибка", "Кошелёк не разблокирован. Подключите USB.")
            return
        if not HAS_QRCODE or not HAS_PIL:
            QMessageBox.warning(self, "Нет зависимостей", "Установите:\npip install qrcode[pil] Pillow")
            return
        try:
            amount = self._qr_amount_input.value() or None
            chain_id = self._eth.chain_id or 1
            pil_img = generate_receive_qr(
                address=self._address,
                amount_eth=amount,
                chain_id=chain_id,
                size=250,
            )
            self._qr_pil_image = pil_img
            self._qr_image_label.setPixmap(_pil_to_pixmap(pil_img))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _save_qr_image(self):
        if not self._qr_pil_image:
            QMessageBox.information(self, "Нет QR", "Сначала сгенерируйте QR-код")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить QR", "qr_receive.png", "PNG (*.png)")
        if path:
            self._qr_pil_image.save(path)
            QMessageBox.information(self, "Сохранено", f"QR сохранён: {path}")

    def _scan_qr_from_file(self):
        if not HAS_CV2:
            QMessageBox.warning(self, "Нет зависимостей", "Установите:\npip install opencv-python")
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл QR", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not path:
            return
        try:
            raw = decode_qr_from_image(path)
            self._qr_uri_input.setText(raw)
            self._parse_qr_uri()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _parse_qr_uri(self):
        raw = self._qr_uri_input.text().strip()
        if not raw:
            return
        try:
            req = parse_qr_uri(raw)
            self._last_qr_request = req
            self._qr_result_addr.setText(req.address)
            self._qr_result_amount.setText(
                f"Сумма: {req.amount_eth} ETH" if req.amount_eth else "Сумма: не указана"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _fill_send_from_qr(self):
        if not self._last_qr_request:
            QMessageBox.information(self, "Нет данных", "Сначала разберите QR")
            return
        req = self._last_qr_request
        self._to_input.setText(req.address)
        if req.amount_eth:
            self._amount_input.setValue(req.amount_eth)
        self._switch_page(1)

    # ─── Send page ─── #

    def _build_send_page(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Отправить ETH")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Создайте транзакцию → сохраните на USB → подпишите офлайн → отправьте")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(14)

        form_layout.addWidget(self._make_field_label("Адрес получателя"))
        self._to_input = QLineEdit()
        self._to_input.setPlaceholderText("0x...")
        form_layout.addWidget(self._to_input)

        form_layout.addWidget(self._make_field_label("Сумма (ETH)"))
        self._amount_input = QDoubleSpinBox()
        self._amount_input.setDecimals(8)
        self._amount_input.setMaximum(1000000)
        self._amount_input.setSingleStep(0.01)
        form_layout.addWidget(self._amount_input)

        gas_group = QFrame()
        gas_group.setObjectName("card")
        gas_layout = QVBoxLayout(gas_group)

        gas_header = QHBoxLayout()
        gas_label = QLabel("Настройки Gas")
        gas_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 15px;")
        gas_header.addWidget(gas_label)

        self._btn_fetch_gas = QPushButton("Получить текущий")
        self._btn_fetch_gas.setObjectName("secondaryBtn")
        self._btn_fetch_gas.setFixedWidth(180)
        self._btn_fetch_gas.clicked.connect(self._fetch_gas_prices)
        gas_header.addWidget(self._btn_fetch_gas)
        gas_layout.addLayout(gas_header)

        gas_layout.addWidget(self._make_field_label("Тип"))
        self._tx_type_combo = QComboBox()
        self._tx_type_combo.addItems(["EIP-1559 (рекомендуется)", "Legacy"])
        self._tx_type_combo.currentIndexChanged.connect(self._on_tx_type_changed)
        gas_layout.addWidget(self._tx_type_combo)

        self._eip1559_widget = QWidget()
        eip_layout = QGridLayout(self._eip1559_widget)
        eip_layout.setContentsMargins(0, 0, 0, 0)

        eip_layout.addWidget(self._make_field_label("Max Fee (Gwei)"), 0, 0)
        self._max_fee_input = QDoubleSpinBox()
        self._max_fee_input.setDecimals(4)
        self._max_fee_input.setMaximum(10000)
        self._max_fee_input.setValue(30)
        eip_layout.addWidget(self._max_fee_input, 1, 0)

        eip_layout.addWidget(self._make_field_label("Priority Fee (Gwei)"), 0, 1)
        self._priority_fee_input = QDoubleSpinBox()
        self._priority_fee_input.setDecimals(4)
        self._priority_fee_input.setMaximum(1000)
        self._priority_fee_input.setValue(1.5)
        eip_layout.addWidget(self._priority_fee_input, 1, 1)

        gas_layout.addWidget(self._eip1559_widget)

        self._legacy_widget = QWidget()
        legacy_layout = QVBoxLayout(self._legacy_widget)
        legacy_layout.setContentsMargins(0, 0, 0, 0)
        legacy_layout.addWidget(self._make_field_label("Gas Price (Gwei)"))
        self._gas_price_input = QDoubleSpinBox()
        self._gas_price_input.setDecimals(4)
        self._gas_price_input.setMaximum(10000)
        self._gas_price_input.setValue(30)
        legacy_layout.addWidget(self._gas_price_input)
        self._legacy_widget.hide()
        gas_layout.addWidget(self._legacy_widget)

        gas_layout.addWidget(self._make_field_label("Gas Limit"))
        self._gas_limit_input = QDoubleSpinBox()
        self._gas_limit_input.setDecimals(0)
        self._gas_limit_input.setMinimum(21000)
        self._gas_limit_input.setMaximum(1000000)
        self._gas_limit_input.setValue(21000)
        gas_layout.addWidget(self._gas_limit_input)

        form_layout.addWidget(gas_group)
        layout.addWidget(form_card)

        btn_layout = QHBoxLayout()
        self._btn_create_tx = QPushButton("Создать TX → USB")
        self._btn_create_tx.setObjectName("primaryBtn")
        self._btn_create_tx.setEnabled(False)
        self._btn_create_tx.clicked.connect(self._create_unsigned_tx)
        btn_layout.addWidget(self._btn_create_tx)
        layout.addLayout(btn_layout)
        layout.addStretch()

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)
        return wrapper

    # ─── Sign page ─── #

    def _build_sign_page(self) -> QWidget:
        page = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        title = QLabel("Транзакции")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        pending_title = QLabel("⯊ ШАГ 1 — Подписать транзакцию (pending → signed)")
        pending_title.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 15px; font-weight: 700; padding: 4px 0;"
        )
        layout.addWidget(pending_title)

        pending_hint = QLabel(
            "Сканируйте USB — найдутся неподписанные транзакции из pending/. "
            "Выберите файл, введите пароль — подписанная TX сохранится в signed/."
        )
        pending_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        pending_hint.setWordWrap(True)
        layout.addWidget(pending_hint)

        pending_card = QFrame()
        pending_card.setObjectName("card")
        pending_card_layout = QVBoxLayout(pending_card)

        self._pending_list_widget = QVBoxLayout()
        pending_card_layout.addLayout(self._pending_list_widget)

        self._no_pending_label = QLabel("Нет неподписанных транзакций на USB")
        self._no_pending_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 20px;")
        self._no_pending_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pending_card_layout.addWidget(self._no_pending_label)

        layout.addWidget(pending_card)

        btn_scan_pending = QPushButton("🔍 Сканировать pending/ на USB")
        btn_scan_pending.setObjectName("primaryBtn")
        btn_scan_pending.clicked.connect(self._scan_pending_txs)
        layout.addWidget(btn_scan_pending)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"color: {COLORS.get('border', '#333')};")
        layout.addWidget(divider)

        signed_title = QLabel("▶ ШАГ 2 — Отправить подписанную транзакцию в сеть")
        signed_title.setStyleSheet(
            f"color: {COLORS.get('success', '#4caf50')}; font-size: 15px; font-weight: 700; padding: 4px 0;"
        )
        layout.addWidget(signed_title)

        signed_hint = QLabel("Файлы из signed/ на USB. Нажмите 'Отправить в сеть' рядом с нужным файлом.")
        signed_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        layout.addWidget(signed_hint)

        signed_card = QFrame()
        signed_card.setObjectName("card")
        signed_card_layout = QVBoxLayout(signed_card)

        self._signed_list_widget = QVBoxLayout()
        signed_card_layout.addLayout(self._signed_list_widget)

        self._no_signed_label = QLabel("Нет подписанных транзакций на USB")
        self._no_signed_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 20px;")
        self._no_signed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signed_card_layout.addWidget(self._no_signed_label)

        layout.addWidget(signed_card)

        btn_scan_signed = QPushButton("🔍 Сканировать signed/ на USB")
        btn_scan_signed.setObjectName("secondaryBtn")
        btn_scan_signed.clicked.connect(self._scan_signed_txs)
        layout.addWidget(btn_scan_signed)

        self._broadcast_log = QTextEdit()
        self._broadcast_log.setReadOnly(True)
        self._broadcast_log.setMaximumHeight(160)
        self._broadcast_log.setPlaceholderText("Лог операций...")
        layout.addWidget(self._broadcast_log)
        layout.addStretch()

        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)
        return wrapper

    # ─── Подпись pending TX ─── #

    def _scan_pending_txs(self):
        if not self._usb_connected:
            QMessageBox.warning(self, "Ошибка", "USB не подключён")
            return

        while self._pending_list_widget.count():
            item = self._pending_list_widget.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pending_files = self._usb.list_pending_txs()
        if not pending_files:
            self._no_pending_label.show()
            return

        self._no_pending_label.hide()

        for fname in pending_files:
            row = QHBoxLayout()
            name_label = QLabel(fname)
            name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
            row.addWidget(name_label)

            btn_sign = QPushButton("✎ Подписать")
            btn_sign.setObjectName("primaryBtn")
            btn_sign.setFixedWidth(160)
            btn_sign.clicked.connect(lambda _, f=fname: self._sign_pending_tx(f))
            row.addWidget(btn_sign)

            w = QWidget()
            w.setLayout(row)
            self._pending_list_widget.addWidget(w)

    def _sign_pending_tx(self, filename: str):
        raw_key = self._km.private_key
        if not raw_key:
            QMessageBox.warning(self, "Ошибка", "Кошелёк не разблокирован. Подключите USB.")
            return

        private_key: bytes = bytes(raw_key)

        try:
            tx_json = self._usb.read_pending_tx(filename)
            tx_data = json.loads(tx_json)
            tx_inner = tx_data.get("tx", tx_data)
            to = tx_inner.get("to", "?")
            value_wei = int(tx_inner.get("value_wei", tx_inner.get("value", 0)))
            value_eth = value_wei / 10 ** 18
            nonce = tx_inner.get("nonce", "?")

            confirm = QMessageBox.question(
                self,
                "Подтвердите подпись",
                f"Получатель: {to}\n"
                f"Сумма: {value_eth:.8f} ETH\n"
                f"Nonce: {nonce}\n\n"
                f"Подписать транзакцию?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm != QMessageBox.StandardButton.Yes:
                return

            tx_req = TransactionSigner.deserialize_unsigned_tx(tx_json)
            signed_hex = TransactionSigner.sign_transaction(
                private_key=private_key,
                tx_request=tx_req,
            )

            signed_filename = filename.replace(".json", "_signed.json")
            path = self._usb.save_signed_tx(signed_hex, signed_filename)
            self._usb.delete_pending_tx(filename)

            self._broadcast_log.append(f"[✓] Подписано: {signed_filename}")
            QMessageBox.information(
                self, "Транзакция подписана",
                f"Файл сохранён: {path}\n\n"
                f"Теперь нажмите 'Сканировать signed/' и 'Отправить в сеть'."
            )
            self._scan_pending_txs()
            self._scan_signed_txs()

        except Exception as e:
            tb = traceback.format_exc()
            if hasattr(self, '_broadcast_log'):
                self._broadcast_log.append(f"[!] Ошибка подписи:\n{tb}")
            QMessageBox.critical(self, "Ошибка подписи", f"{e}\n\nПодробности:\n{tb}")

    # ─── Broadcast signed ─── #

    def _scan_signed_txs(self):
        if not self._usb_connected:
            return

        while self._signed_list_widget.count():
            item = self._signed_list_widget.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        signed_files = self._usb.list_signed_txs()
        if not signed_files:
            self._no_signed_label.show()
            return

        self._no_signed_label.hide()

        for fname in signed_files:
            row = QHBoxLayout()
            name_label = QLabel(fname)
            name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 500;")
            row.addWidget(name_label)

            btn_send = QPushButton("▶ Отправить в сеть")
            btn_send.setObjectName("primaryBtn")
            btn_send.setFixedWidth(180)
            btn_send.clicked.connect(lambda _, f=fname: self._broadcast_signed(f))
            row.addWidget(btn_send)

            w = QWidget()
            w.setLayout(row)
            self._signed_list_widget.addWidget(w)

    def _broadcast_signed(self, filename: str):
        if not self._eth.is_connected:
            if not self._eth.connect():
                QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к сети")
                return
        try:
            data = self._usb.read_signed_tx(filename)
            raw_tx = data.get("raw_tx", "")
            if not raw_tx:
                raise ValueError("Пустой raw_tx в файле")
            self._broadcast_log.append(f"[*] Отправка {filename}...")
            self._tx_worker.send_tx(raw_tx)
        except Exception as e:
            self._broadcast_log.append(f"[!] Ошибка: {e}")

    # ─── Settings ─── #

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Настройки")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        layout.addStretch()
        return page

    # ─── Вспомогательные методы ─── #

    def _make_field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;"
        )
        return lbl

    def _switch_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)

    def _detect_usb(self):
        try:
            drives = USBManager.detect_usb_drives()
            if drives:
                self._usb_connected = True
                drive_info = drives[0]
                drive_path = drive_info["path"]
                drive_label = drive_info.get("label", drive_path)

                self._usb_status.setText(f"● USB: {drive_label}")
                self._usb_status.setStyleSheet(
                    f"color: {COLORS['success']}; font-size: 12px; padding: 4px 8px 16px;"
                )
                if self._usb_display:
                    self._usb_display.setText("Подкл.")

                self._load_wallet_from_usb(drive_path)
            else:
                self._usb_connected = False
                self._usb_status.setText("● USB отключён")
                self._usb_status.setStyleSheet(
                    f"color: {COLORS['error']}; font-size: 12px; padding: 4px 8px 16px;"
                )
        except Exception:
            pass

    def _load_wallet_from_usb(self, drive_path: str):
        try:
            self._usb.set_usb_path(drive_path)

            if not self._usb.is_initialized:
                return

            wallet_file = str(self._usb.wallet_file)

            address = self._unlock_wallet(wallet_file)
            if address is None:
                return

            self._address = address
            short = address[:10] + "…" + address[-8:]
            self._address_label.setText(short)
            self._btn_refresh.setEnabled(True)
            self._btn_create_tx.setEnabled(True)
            self._refresh_balance()
            self._load_tx_history()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка загрузки кошелька", str(e))

    def _unlock_wallet(self, wallet_file: str, max_attempts: int = 3) -> Optional[str]:
        for attempt in range(1, max_attempts + 1):
            hint = "" if attempt == 1 else f"  (попытка {attempt} из {max_attempts})"
            password, ok = QInputDialog.getText(
                self,
                "Разблокировка кошелька",
                f"Введите пароль для кошелька на USB:{hint}",
                QLineEdit.EchoMode.Password,
            )

            if not ok or not password:
                QMessageBox.information(
                    self,
                    "Кошелёк заблокирован",
                    "Кошелёк не разблокирован. Подключите USB и перезапустите приложение."
                )
                return None

            try:
                address = self._km.decrypt_and_load(password, wallet_file)
                return address
            except ValueError:
                remaining = max_attempts - attempt
                if remaining > 0:
                    QMessageBox.warning(
                        self,
                        "Неверный пароль",
                        f"Неверный пароль. Осталось попыток: {remaining}."
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Доступ заблокирован",
                        "Превышено количество попыток ввода пароля.\n"
                        "Перезапустите приложение и попробуйте снова."
                    )
                    return None

        return None

    def _refresh_balance(self):
        if not self._address:
            return
        if not self._eth.is_connected:
            self._eth.connect()
        self._balance_worker.fetch_balance(self._address)
        self._balance_worker.balance_ready.connect(self._on_balance_ready)
        self._nonce_worker.fetch_nonce(self._address)
        self._nonce_worker.nonce_ready.connect(self._on_nonce_ready)

    def _on_balance_ready(self, data: dict):
        eth_val = data.get("eth", "0")
        self._balance_eth = str(eth_val)
        self._update_balance_display()

    def _on_nonce_ready(self, nonce: int):
        self._current_nonce = nonce
        if self._nonce_display:
            self._nonce_display.setText(str(nonce))

    def _fetch_gas_prices(self):
        if not self._eth.is_connected:
            self._eth.connect()
        self._gas_worker.fetch_gas()
        self._gas_worker.gas_ready.connect(self._on_gas_ready)

    def _on_gas_ready(self, data: dict):
        base = data.get("base_fee_gwei", data.get("gas_price_gwei", 0))
        if self._gas_display:
            self._gas_display.setText(f"{base:.1f} Gwei")
        if hasattr(self, "_max_fee_input"):
            self._max_fee_input.setValue(float(base) * 1.2)

    def _on_tx_type_changed(self, idx: int):
        if idx == 0:
            self._eip1559_widget.show()
            self._legacy_widget.hide()
        else:
            self._eip1559_widget.hide()
            self._legacy_widget.show()

    def _create_unsigned_tx(self):
        """
        Создаёт неподписанную транзакцию и сохраняет на USB.
        Конвертирует ETH→Wei и Gwei→Wei перед передачей в TransactionRequest.
        """
        if not self._address or not self._usb_connected:
            QMessageBox.warning(self, "Ошибка", "Кошелёк не разблокирован или USB не подключён.")
            return
        to = self._to_input.text().strip()
        if not to.startswith("0x") or len(to) != 42:
            QMessageBox.warning(self, "Ошибка", "Неверный адрес получателя")
            return
        amount_eth = self._amount_input.value()
        if amount_eth <= 0:
            QMessageBox.warning(self, "Ошибка", "Укажите сумму > 0")
            return
        try:
            use_eip1559 = self._tx_type_combo.currentIndex() == 0

            # Конвертация ETH → Wei
            value_wei = int(amount_eth * 10**18)

            # Конвертация Gwei → Wei
            if use_eip1559:
                max_fee_per_gas = int(self._max_fee_input.value() * 10**9)
                max_priority_fee_per_gas = int(self._priority_fee_input.value() * 10**9)
                gas_price = None
            else:
                max_fee_per_gas = None
                max_priority_fee_per_gas = None
                gas_price = int(self._gas_price_input.value() * 10**9)

            tx_req = TransactionRequest(
                to=to,
                value_wei=value_wei,
                nonce=self._current_nonce,
                chain_id=self._eth.chain_id or 1,
                gas_limit=int(self._gas_limit_input.value()),
                max_fee_per_gas=max_fee_per_gas,
                max_priority_fee_per_gas=max_priority_fee_per_gas,
                gas_price=gas_price,
            )

            tx_json = TransactionSigner.serialize_unsigned_tx(tx_req)
            fname = f"tx_{int(time.time())}.json"
            path = self._usb.save_pending_tx(tx_json, fname)
            QMessageBox.information(
                self, "Транзакция создана",
                f"Сохранено в pending/:\n{path}\n\n"
                f"Перейдите на вкладку 'Подписать & Отправить'."
            )
            self._to_input.clear()
            self._amount_input.setValue(0)

        except Exception as e:
            tb = traceback.format_exc()
            QMessageBox.critical(self, "Ошибка", f"{e}\n\nПодробности:\n{tb}")

    def _connect_signals(self):
        self._balance_worker.error.connect(
            lambda e: self._balance_label.setText(f"Ошибка: {e[:40]}")
        )
        self._tx_worker.tx_sent.connect(self._on_tx_sent)
        self._tx_worker.error.connect(
            lambda e: self._broadcast_log.append(f"[!] {e}") if hasattr(self, '_broadcast_log') else None
        )

    def _on_tx_sent(self, tx_hash: str):
        if hasattr(self, '_broadcast_log'):
            self._broadcast_log.append(f"[✓] TX отправлена: {tx_hash}")
        QMessageBox.information(
            self, "Транзакция отправлена",
            f"Hash: {tx_hash}\n\nПроверьте на Etherscan."
        )


def _pil_to_pixmap(pil_image) -> QPixmap:
    """Конвертирует PIL Image в QPixmap."""
    import io
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)
