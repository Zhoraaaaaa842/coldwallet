"""
ColdVault ETH — Главное окно десктоп-приложения.
Ledger-like дизайн: sidebar навигация, карточка баланса, отправка TX.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QPushButton, QLabel, QLineEdit, QFrame, QMessageBox, QFileDialog,
    QComboBox, QDoubleSpinBox, QTextEdit, QSpacerItem, QSizePolicy,
    QApplication, QProgressBar, QGroupBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QIcon, QClipboard

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cold_wallet.core.key_manager import KeyManager
from cold_wallet.core.transaction import TransactionSigner, TransactionRequest
from cold_wallet.core.eth_network import EthNetwork
from cold_wallet.storage.usb_manager import USBManager
from desktop_app.styles import (
    MAIN_STYLESHEET, COLORS, CARD_BALANCE_STYLE, ETH_ICON_STYLE
)


# ─── Фоновые потоки ─── #

class NetworkWorker(QThread):
    """Поток для сетевых запросов (не блокирует UI)."""
    balance_ready = pyqtSignal(dict)
    gas_ready = pyqtSignal(dict)
    nonce_ready = pyqtSignal(int)
    tx_sent = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, eth_net: EthNetwork):
        super().__init__()
        self._eth = eth_net
        self._task = None
        self._params = {}

    def fetch_balance(self, address: str):
        self._task = "balance"
        self._params = {"address": address}
        self.start()

    def fetch_gas(self):
        self._task = "gas"
        self.start()

    def fetch_nonce(self, address: str):
        self._task = "nonce"
        self._params = {"address": address}
        self.start()

    def send_tx(self, raw_tx: str):
        self._task = "send_tx"
        self._params = {"raw_tx": raw_tx}
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
        except Exception as e:
            self.error.emit(str(e))


# ─── Главное окно ─── #

class ColdVaultMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ColdVault ETH")
        self.setMinimumSize(1100, 720)
        self.resize(1200, 800)

        # Состояние
        self._km = KeyManager()
        self._usb = USBManager()
        self._eth = EthNetwork("mainnet")
        self._worker = NetworkWorker(self._eth)
        self._address: Optional[str] = None
        self._balance_eth = "0"
        self._current_nonce = 0
        self._usb_connected = False

        # UI
        self.setStyleSheet(MAIN_STYLESHEET)
        self._build_ui()
        self._connect_signals()

        # Автообнаружение USB при запуске
        QTimer.singleShot(500, self._detect_usb)

    # ─── Построение UI ─── #

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        # Content area
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_dashboard_page())   # 0
        self._stack.addWidget(self._build_send_page())         # 1
        self._stack.addWidget(self._build_sign_page())         # 2
        self._stack.addWidget(self._build_settings_page())     # 3
        main_layout.addWidget(self._stack, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(4)

        # Лого
        logo = QLabel("◈ ColdVault")
        logo.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-size: 22px;
            font-weight: 700;
            padding: 10px 8px 20px;
        """)
        layout.addWidget(logo)

        # USB статус
        self._usb_status = QLabel("● USB отключён")
        self._usb_status.setObjectName("statusDisconnected")
        self._usb_status.setStyleSheet(f"""
            color: {COLORS['error']};
            font-size: 12px;
            padding: 4px 8px 16px;
        """)
        layout.addWidget(self._usb_status)

        # Навигация
        nav_items = [
            ("⌂  Кошелёк", 0),
            ("↗  Отправить", 1),
            ("✎  Подписать", 2),
            ("⚙  Настройки", 3),
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

        # Сеть
        self._network_label = QLabel("Ethereum Mainnet")
        self._network_label.setObjectName("networkLabel")
        self._network_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._network_label)

        # Версия
        ver = QLabel("v1.0.0")
        ver.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding: 8px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        return sidebar

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Кошелёк")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Карточка баланса
        balance_card = QFrame()
        balance_card.setStyleSheet(CARD_BALANCE_STYLE)
        bc_layout = QVBoxLayout(balance_card)
        bc_layout.setSpacing(8)

        eth_icon = QLabel("Ξ Ethereum")
        eth_icon.setStyleSheet(ETH_ICON_STYLE)
        bc_layout.addWidget(eth_icon)

        self._balance_label = QLabel("— ETH")
        self._balance_label.setObjectName("balanceLabel")
        bc_layout.addWidget(self._balance_label)

        self._address_label = QLabel("Подключите USB для начала работы")
        self._address_label.setObjectName("addressLabel")
        self._address_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._address_label.mousePressEvent = self._copy_address
        bc_layout.addWidget(self._address_label)

        layout.addWidget(balance_card)

        # Кнопки действий
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self._btn_refresh = QPushButton("Обновить баланс")
        self._btn_refresh.setObjectName("primaryBtn")
        self._btn_refresh.setEnabled(False)
        self._btn_refresh.clicked.connect(self._refresh_balance)
        actions_layout.addWidget(self._btn_refresh)

        self._btn_detect_usb = QPushButton("Обнаружить USB")
        self._btn_detect_usb.setObjectName("secondaryBtn")
        self._btn_detect_usb.clicked.connect(self._detect_usb)
        actions_layout.addWidget(self._btn_detect_usb)

        btn_copy = QPushButton("Копировать адрес")
        btn_copy.setObjectName("secondaryBtn")
        btn_copy.clicked.connect(lambda: self._copy_address(None))
        actions_layout.addWidget(btn_copy)

        layout.addLayout(actions_layout)

        # Информационные карточки
        info_grid = QGridLayout()
        info_grid.setSpacing(12)

        # Nonce
        nonce_card = self._make_info_card("Nonce", "—")
        self._nonce_display = nonce_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(nonce_card, 0, 0)

        # Network
        net_card = self._make_info_card("Сеть", "Mainnet")
        self._net_display = net_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(net_card, 0, 1)

        # Gas
        gas_card = self._make_info_card("Gas Price", "—")
        self._gas_display = gas_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(gas_card, 0, 2)

        # USB
        usb_info_card = self._make_info_card("USB", "Не подключён")
        self._usb_display = usb_info_card.findChild(QLabel, "infoValue")
        info_grid.addWidget(usb_info_card, 0, 3)

        layout.addLayout(info_grid)
        layout.addStretch()

        return page

    def _make_info_card(self, title: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(6)

        t = QLabel(title)
        t.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-weight: 600;")
        card_layout.addWidget(t)

        v = QLabel(value)
        v.setObjectName("infoValue")
        v.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 18px; font-weight: 700;")
        card_layout.addWidget(v)

        return card

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

        subtitle = QLabel(
            "Создайте транзакцию → сохраните на USB → подпишите офлайн → отправьте"
        )
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        # Форма
        form_card = QFrame()
        form_card.setObjectName("card")
        form_layout = QVBoxLayout(form_card)
        form_layout.setSpacing(14)

        # Адрес получателя
        form_layout.addWidget(self._make_field_label("Адрес получателя"))
        self._to_input = QLineEdit()
        self._to_input.setPlaceholderText("0x...")
        form_layout.addWidget(self._to_input)

        # Сумма
        form_layout.addWidget(self._make_field_label("Сумма (ETH)"))
        self._amount_input = QDoubleSpinBox()
        self._amount_input.setDecimals(8)
        self._amount_input.setMaximum(1000000)
        self._amount_input.setSingleStep(0.01)
        form_layout.addWidget(self._amount_input)

        # Gas настройки
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

        # Тип транзакции
        gas_layout.addWidget(self._make_field_label("Тип"))
        self._tx_type_combo = QComboBox()
        self._tx_type_combo.addItems(["EIP-1559 (рекомендуется)", "Legacy"])
        self._tx_type_combo.currentIndexChanged.connect(self._on_tx_type_changed)
        gas_layout.addWidget(self._tx_type_combo)

        # EIP-1559 fields
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

        # Legacy field
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

        # Gas limit
        gas_layout.addWidget(self._make_field_label("Gas Limit"))
        self._gas_limit_input = QDoubleSpinBox()
        self._gas_limit_input.setDecimals(0)
        self._gas_limit_input.setMinimum(21000)
        self._gas_limit_input.setMaximum(1000000)
        self._gas_limit_input.setValue(21000)
        gas_layout.addWidget(self._gas_limit_input)

        form_layout.addWidget(gas_group)

        layout.addWidget(form_card)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._btn_create_tx = QPushButton("Создать TX → USB")
        self._btn_create_tx.setObjectName("primaryBtn")
        self._btn_create_tx.setEnabled(False)
        self._btn_create_tx.clicked.connect(self._create_unsigned_tx)
        btn_layout.addWidget(self._btn_create_tx)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # Оборачиваем в scroll
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)
        return wrapper

    def _build_sign_page(self) -> QWidget:
        """Страница для broadcast подписанных TX."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Подписанные транзакции")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel(
            "Подключите USB с подписанными транзакциями для отправки в сеть"
        )
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        # Список signed TX
        self._signed_list_widget = QVBoxLayout()
        signed_card = QFrame()
        signed_card.setObjectName("card")
        signed_layout = QVBoxLayout(signed_card)
        signed_layout.addLayout(self._signed_list_widget)

        self._no_signed_label = QLabel("Нет подписанных транзакций на USB")
        self._no_signed_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 20px;")
        self._no_signed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signed_layout.addWidget(self._no_signed_label)

        layout.addWidget(signed_card)

        # Кнопки
        btn_layout = QHBoxLayout()

        self._btn_scan_signed = QPushButton("Сканировать USB")
        self._btn_scan_signed.setObjectName("secondaryBtn")
        self._btn_scan_signed.clicked.connect(self._scan_signed_txs)
        btn_layout.addWidget(self._btn_scan_signed)

        layout.addLayout(btn_layout)

        # Лог
        self._broadcast_log = QTextEdit()
        self._broadcast_log.setReadOnly(True)
        self._broadcast_log.setMaximumHeight(200)
        self._broadcast_log.setPlaceholderText("Лог отправки транзакций...")
        layout.addWidget(self._broadcast_log)

        layout.addStretch()
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        title = QLabel("Настройки")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Сеть
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

        # USB вручную
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

        # Безопасность
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
        label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 13px;
            font-weight: 600;
            padding-top: 4px;
        """)
        return label

    # ─── Сигналы ─── #

    def _connect_signals(self):
        self._worker.balance_ready.connect(self._on_balance_received)
        self._worker.gas_ready.connect(self._on_gas_received)
        self._worker.nonce_ready.connect(self._on_nonce_received)
        self._worker.tx_sent.connect(self._on_tx_sent)
        self._worker.error.connect(self._on_network_error)

    # ─── Навигация ─── #

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

        # Ищем USB с ColdVault
        for drive in drives:
            vault = Path(drive["path"]) / "ColdVault" / "wallet.vault"
            if vault.exists():
                self._usb.set_usb_path(drive["path"])
                self._set_usb_status(True, f"{drive['label']} ({drive['size']})")
                self._unlock_wallet_dialog()
                return

        # Если ColdVault не найден, берём первый USB
        d = drives[0]
        self._set_usb_status(False, f"{d['label']} (нет кошелька)")

    def _set_usb_status(self, connected: bool, info: str):
        self._usb_connected = connected
        if connected:
            self._usb_status.setText(f"● USB подключён")
            self._usb_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; padding: 4px 8px 16px;")
            if self._usb_display:
                self._usb_display.setText(info)
        else:
            self._usb_status.setText(f"● USB отключён")
            self._usb_status.setStyleSheet(f"color: {COLORS['error']}; font-size: 12px; padding: 4px 8px 16px;")
            if self._usb_display:
                self._usb_display.setText(info)

    def _unlock_wallet_dialog(self):
        """Диалог ввода пароля для разблокировки."""
        from PyQt6.QtWidgets import QInputDialog
        password, ok = QInputDialog.getText(
            self, "ColdVault — Разблокировка",
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
        """Подключение к сети и загрузка данных."""
        if self._eth.connect():
            self._refresh_balance()
            self._fetch_gas_prices()

    def _refresh_balance(self):
        if self._address and self._eth.is_connected:
            self._balance_label.setText("Загрузка...")
            self._worker.fetch_balance(self._address)
            self._worker.fetch_nonce(self._address)

    def _fetch_gas_prices(self):
        if self._eth.is_connected:
            self._worker.fetch_gas()

    # ─── Callbacks ─── #

    def _on_balance_received(self, data: dict):
        eth = data.get("eth", "0")
        self._balance_eth = eth
        self._balance_label.setText(f"{eth} ETH")

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

    def _on_network_error(self, error: str):
        self._broadcast_log.append(f"[!] Ошибка: {error}")

    # ─── Создание TX ─── #

    def _create_unsigned_tx(self):
        """Создаёт unsigned TX и сохраняет на USB."""
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
                # EIP-1559
                tx.max_fee_per_gas = EthNetwork.gwei_to_wei(self._max_fee_input.value())
                tx.max_priority_fee_per_gas = EthNetwork.gwei_to_wei(self._priority_fee_input.value())
            else:
                # Legacy
                tx.gas_price = EthNetwork.gwei_to_wei(self._gas_price_input.value())

            tx.validate()

            # Сериализация
            tx_json = TransactionSigner.serialize_unsigned_tx(tx)
            filename = f"tx_{self._current_nonce}_{int(time.time())}.json"
            path = self._usb.save_pending_tx(tx_json, filename)

            QMessageBox.information(
                self, "TX создана",
                f"Транзакция сохранена на USB:\n{path}\n\n"
                f"Перенесите USB на офлайн-ПК для подписи."
            )

            # Очистка формы
            self._to_input.clear()
            self._amount_input.setValue(0)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    # ─── Broadcast signed TX ─── #

    def _scan_signed_txs(self):
        """Сканирует USB на подписанные TX."""
        if not self._usb_connected:
            QMessageBox.warning(self, "Ошибка", "USB не подключён")
            return

        # Очищаем старый список
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

            btn_send = QPushButton("Отправить в сеть")
            btn_send.setObjectName("primaryBtn")
            btn_send.setFixedWidth(180)
            btn_send.clicked.connect(lambda _, f=fname: self._broadcast_signed(f))
            row.addWidget(btn_send)

            wrapper = QWidget()
            wrapper.setLayout(row)
            self._signed_list_widget.addWidget(wrapper)

    def _broadcast_signed(self, filename: str):
        """Отправляет подписанную TX в сеть."""
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
            self._worker.send_tx(raw_tx)

        except Exception as e:
            self._broadcast_log.append(f"[!] Ошибка: {e}")

    # ─── Settings ─── #

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
        self._worker = NetworkWorker(self._eth)
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
            self._worker = NetworkWorker(self._eth)
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
                QMessageBox.warning(
                    self, "Внимание",
                    "ColdVault не найден на этом USB.\n"
                    "Используйте install_to_usb.py для установки."
                )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _lock_wallet(self):
        self._km.clear()
        self._address = None
        self._balance_label.setText("— ETH")
        self._address_label.setText("Кошелёк заблокирован")
        self._btn_refresh.setEnabled(False)
        self._btn_create_tx.setEnabled(False)

    def _copy_address(self, event):
        if self._address:
            clipboard = QApplication.clipboard()
            clipboard.setText(self._address)

    # ─── Cleanup ─── #

    def closeEvent(self, event):
        self._km.clear()
        event.accept()
