"""
ColdVault ETH — Стили PyQt6 в стиле Ledger Live.
Тёмная тема с акцентным фиолетовым (#A855F7) на чёрном фоне.
"""

COLORS = {
    "bg_primary":   "#0F0F13",
    "bg_secondary": "#17171C",
    "bg_tertiary":  "#1E1E26",
    "bg_hover":     "#252530",
    "border":       "#2A2A35",
    "border_focus": "#A855F7",
    "text_primary": "#FFFFFF",
    "text_secondary": "#9CA3AF",
    "text_muted":   "#6B7280",
    "accent":       "#A855F7",
    "accent_hover": "#9333EA",
    "accent_dark":  "#7C3AED",
    "success":      "#22C55E",
    "warning":      "#F59E0B",
    "error":        "#EF4444",
    "eth_blue":     "#627EEA",
}


MAIN_STYLESHEET = f"""
    /* ─── Глобальные — ТОЛЬКО цвет текста и шрифт, БЕЗ background ─── */
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    QWidget {{
        color: {COLORS['text_primary']};
        font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif;
        font-size: 14px;
    }}

    /* Фон задаём явно только нужным корневым контейнерам */
    QStackedWidget,
    QScrollArea > QWidget > QWidget {{
        background-color: {COLORS['bg_primary']};
    }}

    /* ─── Sidebar ─── */
    QWidget#sidebar {{
        background-color: {COLORS['bg_secondary']};
        border-right: 1px solid {COLORS['border']};
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

    /* ─── Карточки ─── */
    QFrame#card {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 20px;
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

    QTextEdit {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
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

    QLabel#networkLabel {{
        color: {COLORS['eth_blue']};
        font-size: 12px;
        font-weight: 600;
        background-color: rgba(98, 126, 234, 0.15);
        border-radius: 6px;
        padding: 4px 10px;
    }}

    /* ─── ScrollArea ─── */
    QScrollArea {{
        border: none;
        background: transparent;
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

    QToolTip {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
    }}
"""


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
