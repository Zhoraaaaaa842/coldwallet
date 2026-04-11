"""
ColdVault ETH — Стили PyQt6 в стиле Ledger Live.
Тёмная тема с акцентным фиолетовым (#A855F7) на чёрном фоне.
"""

# Цветовая палитра (Ledger-inspired)
COLORS = {
    "bg_primary": "#0F0F13",        # Основной фон
    "bg_secondary": "#17171C",      # Фон карточек
    "bg_tertiary": "#1E1E26",       # Фон полей ввода
    "bg_hover": "#252530",          # Hover-эффект
    "border": "#2A2A35",            # Границы
    "border_focus": "#A855F7",      # Граница в фокусе
    "text_primary": "#FFFFFF",      # Основной текст
    "text_secondary": "#9CA3AF",    # Вторичный текст
    "text_muted": "#6B7280",        # Приглушённый текст
    "accent": "#A855F7",            # Акцент (фиолетовый Ledger)
    "accent_hover": "#9333EA",      # Акцент при hover
    "accent_dark": "#7C3AED",       # Тёмный акцент
    "success": "#22C55E",           # Успех
    "warning": "#F59E0B",           # Предупреждение
    "error": "#EF4444",             # Ошибка
    "eth_blue": "#627EEA",          # Цвет ETH
}


MAIN_STYLESHEET = f"""
    /* ─── Глобальные стили ─── */
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    QWidget {{
        background-color: {COLORS['bg_primary']};
        color: {COLORS['text_primary']};
        font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif;
        font-size: 14px;
    }}

    /* ─── Sidebar: фон только у самого sidebar, дочерние прозрачны ─── */
    QWidget#sidebar {{
        background-color: {COLORS['bg_secondary']};
        border-right: 1px solid {COLORS['border']};
    }}

    QWidget#sidebar QWidget,
    QWidget#sidebar QLabel,
    QWidget#sidebar QPushButton {{
        background-color: transparent;
    }}

    QPushButton#sidebarBtn {{
        background-color: transparent;
        color: {COLORS['text_secondary']};
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 14px;
        font-weight: 500;
    }}

    QPushButton#sidebarBtn:hover {{
        background-color: {COLORS['bg_hover']};
        color: {COLORS['text_primary']};
    }}

    QPushButton#sidebarBtn:checked {{
        background-color: {COLORS['accent']};
        color: {COLORS['text_primary']};
    }}

    /* ─── Кнопки ─── */
    QPushButton#primaryBtn {{
        background-color: {COLORS['accent']};
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 15px;
        font-weight: 600;
        min-height: 44px;
    }}

    QPushButton#primaryBtn:hover {{
        background-color: {COLORS['accent_hover']};
    }}

    QPushButton#primaryBtn:pressed {{
        background-color: {COLORS['accent_dark']};
    }}

    QPushButton#primaryBtn:disabled {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_muted']};
    }}

    QPushButton#secondaryBtn {{
        background-color: transparent;
        color: {COLORS['accent']};
        border: 2px solid {COLORS['accent']};
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 15px;
        font-weight: 600;
        min-height: 44px;
    }}

    QPushButton#secondaryBtn:hover {{
        background-color: rgba(168, 85, 247, 0.1);
    }}

    QPushButton#dangerBtn {{
        background-color: {COLORS['error']};
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-size: 15px;
        font-weight: 600;
        min-height: 44px;
    }}

    QPushButton#dangerBtn:hover {{
        background-color: #DC2626;
    }}

    /* ─── Поля ввода ─── */
    QLineEdit {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
        selection-background-color: {COLORS['accent']};
    }}

    QLineEdit:focus {{
        border: 2px solid {COLORS['border_focus']};
    }}

    QLineEdit:disabled {{
        color: {COLORS['text_muted']};
    }}

    /* ─── Карточки ─── */
    QFrame#card {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 20px;
    }}

    /* ─── Labels ─── */
    QLabel#titleLabel {{
        color: {COLORS['text_primary']};
        font-size: 28px;
        font-weight: 700;
    }}

    QLabel#subtitleLabel {{
        color: {COLORS['text_secondary']};
        font-size: 14px;
        font-weight: 400;
    }}

    QLabel#balanceLabel {{
        color: {COLORS['text_primary']};
        font-size: 42px;
        font-weight: 700;
    }}

    QLabel#addressLabel {{
        color: {COLORS['text_secondary']};
        font-size: 13px;
        font-family: 'Consolas', 'Courier New', monospace;
    }}

    QLabel#statusConnected {{
        color: {COLORS['success']};
        font-size: 13px;
        font-weight: 600;
    }}

    QLabel#statusDisconnected {{
        color: {COLORS['error']};
        font-size: 13px;
        font-weight: 600;
    }}

    QLabel#networkLabel {{
        color: {COLORS['eth_blue']};
        font-size: 12px;
        font-weight: 600;
        background-color: rgba(98, 126, 234, 0.15);
        border-radius: 6px;
        padding: 4px 10px;
    }}

    /* ─── ComboBox ─── */
    QComboBox {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QComboBox:focus {{
        border: 2px solid {COLORS['border_focus']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['accent']};
    }}

    /* ─── ScrollArea ─── */
    QScrollArea {{
        border: none;
    }}

    QScrollBar:vertical {{
        background-color: {COLORS['bg_primary']};
        width: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 4px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    /* ─── SpinBox ─── */
    QSpinBox, QDoubleSpinBox {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 2px solid {COLORS['border']};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 2px solid {COLORS['border_focus']};
    }}

    /* ─── Tab Widget ─── */
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        background-color: {COLORS['bg_secondary']};
    }}

    QTabBar::tab {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: none;
        padding: 10px 20px;
        font-weight: 500;
    }}

    QTabBar::tab:selected {{
        background-color: {COLORS['accent']};
        color: white;
        border-radius: 6px 6px 0 0;
    }}

    /* ─── TextEdit (для логов) ─── */
    QTextEdit {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
    }}

    /* ─── ProgressBar ─── */
    QProgressBar {{
        background-color: {COLORS['bg_tertiary']};
        border: none;
        border-radius: 6px;
        height: 8px;
        text-align: center;
        color: transparent;
    }}

    QProgressBar::chunk {{
        background-color: {COLORS['accent']};
        border-radius: 6px;
    }}

    /* ─── Tooltips ─── */
    QToolTip {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
    }}
"""


# Дополнительные стили для специфических виджетов
CARD_BALANCE_STYLE = f"""
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1A1033,
        stop:0.5 #1C1040,
        stop:1 #0F0F13
    );
    border: 1px solid {COLORS['accent']};
    border-radius: 20px;
    padding: 30px;
"""

ETH_ICON_STYLE = f"""
    color: {COLORS['eth_blue']};
    font-size: 36px;
    font-weight: 700;
"""
