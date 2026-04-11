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

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QLineEdit, QFrame, QMessageBox, QFileDialog,
    QComboBox, QDoubleSpinBox, QTextEdit, QSpacerItem, QSizePolicy,
    QApplication, QProgressBar, QGroupBox, QGridLayout, QScrollArea,
    QInputDialog, QButtonGroup
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
    def __init__(self, tx: dict, my_address: str, parent=None):
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

        # Правый блок: сумма + статус
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setSpacing(4)

        value_wei = int(tx.get("value", 0))
        value_eth = value_wei / 10**18
        sign = "+" if is_incoming else "−"
        amount_lbl = QLabel(f"{sign}{value_eth:.6f} ETH")
        amount_lbl.setStyleSheet(
            f"color: {icon_color}; font-size: 14px; font-weight: 700;"
        )
        amount_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(amount_lbl)

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
        self._address: Optional[str] = None
        self._balance_eth = "0"
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

    # ─── Dashboard (редизайн) ─── #

    def _build_dashboard_page(self) -> QWidget:
        wrapper = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(wrapper)
        scroll.setObjectName("dashScroll")

        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(18)

        # ── Заголовок страницы ──
        header = QHBoxLayout()
        title = QLabel("Кошелёк")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        subtitle = QLabel("Ethereum · Основная сеть")
        subtitle.setObjectName("subtitleLabel")
        header.addWidget(subtitle)
        layout.addLayout(header)

        # ── Карточка баланса (градиент, крупный дизайн) ──
        balance_card = QFrame()
        balance_card.setStyleSheet(CARD_BALANCE_STYLE)
        bc_layout = QVBoxLayout(balance_card)
        bc_layout.setSpacing(6)
        bc_layout.setContentsMargins(28, 24, 28, 24)

        # Строка: иконка ETH + сеть
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

        # Заголовок баланса
        bal_title = QLabel("Баланс")
        bal_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; margin-top: 8px;")
        bc_layout.addWidget(bal_title)

        self._balance_label = QLabel("—")
        self._balance_label.setObjectName("balanceLabel")
        bc_layout.addWidget(self._balance_label)

        self._balance_eth_label = QLabel("—")
        self._balance_eth_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 15px;"
        )
        bc_layout.addWidget(self._balance_eth_label)

        # Адрес (кликабельный)
        self._address_label = QLabel("Подключите USB для начала работы")
        self._address_label.setObjectName("addressLabel")
        self._address_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._address_label.setToolTip("Нажмите для копирования")
        self._address_label.mousePressEvent = self._copy_address
        self._address_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
            f" font-family: Consolas, monospace; margin-top: 6px;"
        )
        bc_layout.addWidget(self._address_label)

        layout.addWidget(balance_card)

        # ── Панель действий: 4 кнопки ──
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

        # ── Кнопка Etherscan (полная ширина, синяя) ──
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

        # ── Инфо-карточки (Nonce / Сеть / Gas / USB) ──
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

        # ── Заголовок истории транзакций ──
        tx_header = QHBoxLayout()
        tx_title = QLabel("История транзакций")
        tx_title.setStyleSheet(
            f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: 700;"
        )
        tx_header.addWidget(tx_title)
        tx_header.addStretch()

        # Кнопка «Обозреватель →» в заголовке
        btn_open_explorer = QPushButton("Обозреватель →")
        btn_open_explorer.setStyleSheet(
            f"color: {COLORS['accent']}; background: transparent; border: none;"
            f" font-size: 13px; font-weight: 600; padding: 0;"
        )
        btn_open_explorer.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_explorer.clicked.connect(self._open_etherscan)
        tx_header.addWidget(btn_open_explorer)
        layout.addLayout(tx_header)

        # ── Фильтры транзакций ──
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

        # ── Контейнер списка транзакций ──
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

    # ─── Рендер списка транзакций ─── #

    def _render_tx_list(self, txs: list):
        # Чистим старые виджеты
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

        # Группировка по дате
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
                item = TxItemWidget(tx, self._address or "")
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

    # ─── Инфо-карточки ─── #

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

    # ─── Страница Получить (QR) ─── #

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

        net_card = QFrame()
        net_card.setObjectName("card")
        net_layout = QVBoxLayout(net_card)

        net_layout.addWidget(self._make_field_label("Сеть Ethereum"))
        self._network_combo = QComboBox()
        self._network_combo.addItems(["Ethereum Mainnet", "Sepolia Testnet"])
        self._network_combo.currentIndexChanged.connect(self._change_network)
        net_layout.addWidget(self._network_combo)

        net_layout.addWidget(self._make_field_label("Custom RPC URL (опционально)"))
        self._rpc_input = QLineEdit()
        self._rpc_input.setPlaceholderText("https://...")
        net_layout.addWidget(self._rpc_input)

        btn_apply_rpc = QPushButton("Применить")
        btn_apply_rpc.setObjectName("primaryBtn")
        btn_apply_rpc.clicked.connect(self._apply_custom_rpc)
        net_layout.addWidget(btn_apply_rpc)
        layout.addWidget(net_card)

        usb_card = QFrame()
        usb_card.setObjectName("card")
        usb_layout = QVBoxLayout(usb_card)

        usb_layout.addWidget(self._make_field_label("USB путь (вручную)"))
        self._manual_usb_input = QLineEdit()
        self._manual_usb_input.setPlaceholderText("D:\\ или /media/usb")
        usb_layout.addWidget(self._manual_usb_input)

        btn_row = QHBoxLayout()
        btn_browse = QPushButton("Обзор...")
        btn_browse.setObjectName("secondaryBtn")
        btn_browse.clicked.connect(self._browse_usb)
        btn_row.addWidget(btn_browse)

        btn_connect_manual = QPushButton("Подключить")
        btn_connect_manual.setObjectName("primaryBtn")
        btn_connect_manual.clicked.connect(self._connect_manual_usb)
        btn_row.addWidget(btn_connect_manual)
        usb_layout.addLayout(btn_row)
        layout.addWidget(usb_card)

        sec_card = QFrame()
        sec_card.setObjectName("card")
        sec_layout = QVBoxLayout(sec_card)

        sec_title = QLabel("Безопасность")
        sec_title.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 700; font-size: 18px;")
        sec_layout.addWidget(sec_title)

        btn_lock = QPushButton("Заблокировать кошелёк")
        btn_lock.setObjectName("dangerBtn")
        btn_lock.clicked.connect(self._lock_wallet)
        sec_layout.addWidget(btn_lock)
        layout.addWidget(sec_card)
        layout.addStretch()

        return page

    def _make_field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
            f" font-weight: 600; padding-top: 4px;"
        )
        return label

    # ─── Сигналы ─── #

    def _connect_signals(self):
        self._balance_worker.balance_ready.connect(self._on_balance_received)
        self._balance_worker.error.connect(self._on_network_error)
        self._nonce_worker.nonce_ready.connect(self._on_nonce_received)
        self._nonce_worker.error.connect(self._on_network_error)
        self._gas_worker.gas_ready.connect(self._on_gas_received)
        self._gas_worker.error.connect(self._on_network_error)
        self._tx_worker.tx_sent.connect(self._on_tx_sent)
        self._tx_worker.error.connect(self._on_network_error)

    def _switch_page(self, idx: int):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == idx)

    # ─── USB ─── #

    def _detect_usb(self):
        drives = USBManager.detect_usb_drives()
        if not drives:
            self._set_usb_status(False, "USB не обнаружен")
            return

        for drive in drives:
            vault = Path(drive["path"]) / "ColdVault" / "wallet.vault"
            if vault.exists():
                self._usb.set_usb_path(drive["path"])
                label = drive["label"]
                size = drive["size"]
                self._set_usb_status(True, f"{label} ({size})")
                self._unlock_wallet_dialog()
                return

        d = drives[0]
        self._set_usb_status(False, f"{d['label']} (нет кошелька)")

    def _set_usb_status(self, connected: bool, info: str):
        self._usb_connected = connected
        if connected:
            self._usb_status.setText("● USB подключён")
            self._usb_status.setStyleSheet(
                f"color: {COLORS['success']}; font-size: 12px; padding: 4px 8px 16px;"
            )
        else:
            self._usb_status.setText("● USB отключён")
            self._usb_status.setStyleSheet(
                f"color: {COLORS['error']}; font-size: 12px; padding: 4px 8px 16px;"
            )
        if self._usb_display:
            self._usb_display.setText(info)

    def _unlock_wallet_dialog(self):
        password, ok = QInputDialog.getText(
            self, "ZhoraWallet — Разблокировка",
            "Введите пароль кошелька:",
            QLineEdit.EchoMode.Password
        )
        if ok and password:
            try:
                wallet_path = str(self._usb.wallet_file)
                self._address = self._km.decrypt_and_load(password, wallet_path)
                self._address_label.setText(self._address)
                self._btn_refresh.setEnabled(True)
                self._btn_create_tx.setEnabled(True)
                self._connect_network()
            except ValueError as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def _connect_network(self):
        if self._eth.connect():
            self._refresh_balance()
            self._fetch_gas_prices()
            QTimer.singleShot(1000, self._load_tx_history)

    def _refresh_balance(self):
        if self._address and self._eth.is_connected:
            self._balance_label.setText("Загрузка...")
            self._balance_worker.fetch_balance(self._address)
            QTimer.singleShot(500, lambda: self._nonce_worker.fetch_nonce(self._address))

    def _fetch_gas_prices(self):
        if self._eth.is_connected:
            self._gas_worker.fetch_gas()

    def _on_balance_received(self, data: dict):
        eth = data.get("eth", "0")
        self._balance_eth = eth
        self._balance_label.setText(f"{eth} ETH")
        self._balance_eth_label.setText(f"{eth} ETH")

    def _on_nonce_received(self, nonce: int):
        self._current_nonce = nonce
        if self._nonce_display:
            self._nonce_display.setText(str(nonce))

    def _on_gas_received(self, data: dict):
        if data.get("supports_eip1559"):
            base = data.get("base_fee_gwei", 0)
            if self._gas_display:
                self._gas_display.setText(f"{base} Gwei")
            self._max_fee_input.setValue(data.get("max_fee_medium_gwei", 30))
            self._priority_fee_input.setValue(data.get("priority_fee_medium_gwei", 1.5))
        else:
            legacy = data.get("legacy_gas_price_gwei", 0)
            if self._gas_display:
                self._gas_display.setText(f"{legacy} Gwei")
            self._gas_price_input.setValue(legacy)

    def _on_tx_sent(self, tx_hash: str):
        self._broadcast_log.append(f"[✓] TX отправлена: {tx_hash}")
        QMessageBox.information(
            self, "Транзакция отправлена",
            f"TX Hash:\n{tx_hash}\n\nОтслеживайте на etherscan.io"
        )
        QTimer.singleShot(3000, self._load_tx_history)

    def _on_network_error(self, error: str):
        if hasattr(self, '_broadcast_log'):
            self._broadcast_log.append(f"[!] Ошибка: {error}")

    def _create_unsigned_tx(self):
        if not self._address:
            QMessageBox.warning(self, "Ошибка", "Кошелёк не разблокирован")
            return
        if not self._usb_connected:
            QMessageBox.warning(self, "Ошибка", "USB не подключён")
            return

        to_addr = self._to_input.text().strip()
        amount_eth = self._amount_input.value()

        if not to_addr:
            QMessageBox.warning(self, "Ошибка", "Введите адрес получателя")
            return

        try:
            value_wei = EthNetwork.eth_to_wei(amount_eth)
            gas_limit = int(self._gas_limit_input.value())

            tx = TransactionRequest(
                to=to_addr,
                value_wei=value_wei,
                nonce=self._current_nonce,
                chain_id=self._eth.chain_id,
                gas_limit=gas_limit,
            )

            if self._tx_type_combo.currentIndex() == 0:
                tx.max_fee_per_gas = EthNetwork.gwei_to_wei(self._max_fee_input.value())
                tx.max_priority_fee_per_gas = EthNetwork.gwei_to_wei(self._priority_fee_input.value())
            else:
                tx.gas_price = EthNetwork.gwei_to_wei(self._gas_price_input.value())

            tx.validate()

            tx_json = TransactionSigner.serialize_unsigned_tx(tx)
            filename = f"tx_{self._current_nonce}_{int(time.time())}.json"
            path = self._usb.save_pending_tx(tx_json, filename)

            QMessageBox.information(
                self, "TX создана",
                f"Транзакция сохранена на USB:\n{path}\n\n"
                f"Теперь перейдите во вкладку 'Подписать & Отправить' → Сканировать pending/"
            )
            self._to_input.clear()
            self._amount_input.setValue(0)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _on_tx_type_changed(self, idx: int):
        if idx == 0:
            self._eip1559_widget.show()
            self._legacy_widget.hide()
        else:
            self._eip1559_widget.hide()
            self._legacy_widget.show()

    def _change_network(self, idx: int):
        network = "mainnet" if idx == 0 else "sepolia"
        self._eth = EthNetwork(network)
        self._balance_worker = NetworkWorker(self._eth)
        self._nonce_worker = NetworkWorker(self._eth)
        self._gas_worker = NetworkWorker(self._eth)
        self._tx_worker = NetworkWorker(self._eth)
        self._history_worker = NetworkWorker(self._eth)
        self._connect_signals()
        name = "Ethereum Mainnet" if idx == 0 else "Sepolia Testnet"
        self._network_label.setText(name)
        if self._net_display:
            self._net_display.setText(name.split()[0])

    def _apply_custom_rpc(self):
        url = self._rpc_input.text().strip()
        if url:
            network = "mainnet" if self._network_combo.currentIndex() == 0 else "sepolia"
            self._eth = EthNetwork(network, custom_rpc=url)
            self._balance_worker = NetworkWorker(self._eth)
            self._nonce_worker = NetworkWorker(self._eth)
            self._gas_worker = NetworkWorker(self._eth)
            self._tx_worker = NetworkWorker(self._eth)
            self._history_worker = NetworkWorker(self._eth)
            self._connect_signals()
            if self._eth.connect():
                QMessageBox.information(self, "Успех", f"Подключено к {url}")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к {url}")

    def _browse_usb(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите USB накопитель")
        if path:
            self._manual_usb_input.setText(path)

    def _connect_manual_usb(self):
        path = self._manual_usb_input.text().strip()
        if not path:
            return
        try:
            self._usb.set_usb_path(path)
            if self._usb.is_initialized:
                self._set_usb_status(True, path)
                self._unlock_wallet_dialog()
            else:
                QMessageBox.warning(self, "Внимание", "ColdVault не найден на этом USB.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _lock_wallet(self):
        self._km.clear()
        self._address = None
        self._balance_label.setText("—")
        self._balance_eth_label.setText("—")
        self._address_label.setText("Кошелёк заблокирован")
        self._btn_refresh.setEnabled(False)
        self._btn_create_tx.setEnabled(False)
        self._all_txs = []
        self._render_tx_list([])

    def _copy_address(self, event):
        if self._address:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._address)

    def closeEvent(self, event):
        self._km.clear()
        event.accept()


def _pil_to_pixmap(pil_img) -> QPixmap:
    import io
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    qimg = QImage()
    qimg.loadFromData(buf.read())
    return QPixmap.fromImage(qimg)
