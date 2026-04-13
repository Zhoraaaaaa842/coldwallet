"""
ColdVault ETH — Стили PyQt6.
Строгая чёрная тема с белым акцентом.
"""

COLORS = {
    "bg_primary":     "#000000",
    "bg_secondary":   "#0A0A0A",
    "bg_tertiary":    "#111111",
    "bg_hover":       "#1A1A1A",
    "border":         "#222222",
    "border_focus":   "#444444",
    "text_primary":   "#FFFFFF",
    "text_secondary": "#AAAAAA",
    "text_muted":     "#555555",
    "accent":         "#FFFFFF",
    "accent_hover":   "#CCCCCC",
    "accent_dark":    "#999999",
    "success":        "#22C55E",
    "warning":        "#F59E0B",
    "error":          "#EF4444",
    "eth_blue":       "#AAAAAA",
}


MAIN_STYLESHEET = f"""
    QMainWindow {{
        background-color: {COLORS['bg_primary']};
    }}

    QWidget {{
        color: {COLORS['text_primary']};
        font-family: 'Segoe UI', 'Inter', 'Arial', sans-serif;
        font-size: 14px;
        background-color: {COLORS['bg_primary']};
    }}

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
        border-radius: 6px;
        padding: 12px 16px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
    }}

    QPushButton#sidebarBtn:hover {{
        background-color: {COLORS['bg_hover']};
        color: {COLORS['text_primary']};
    }}

    QPushButton#sidebarBtn:checked {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border-left: 2px solid {COLORS['text_primary']};
    }}

    /* ─── Карточки ─── */
    QFrame#card {{
        background-color: {COLORS['bg_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 20px;
    }}

    /* ─── Основная кнопка ─── */
    QPushButton#primaryBtn {{
        background-color: {COLORS['text_primary']};
        color: {COLORS['bg_primary']};
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 700;
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
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 600;
        min-height: 44px;
    }}

    QPushButton#secondaryBtn:hover {{
        background-color: {COLORS['bg_hover']};
        color: {COLORS['text_primary']};
        border-color: {COLORS['border_focus']};
    }}

    QPushButton#maxBtn {{
        background-color: {COLORS['bg_tertiary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_focus']};
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 700;
        min-height: 32px;
    }}

    QPushButton#maxBtn:hover {{
        background-color: {COLORS['bg_hover']};
        border-color: {COLORS['text_primary']};
    }}

    QPushButton#dangerBtn {{
        background-color: {COLORS['error']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: 600;
        min-height: 44px;
    }}

    QPushButton#dangerBtn:hover {{
        background-color: #DC2626;
    }}

    /* ─── Поля ввода ─── */
    QLineEdit {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
        selection-background-color: {COLORS['bg_hover']};
    }}

    QLineEdit:focus {{
        border: 1px solid {COLORS['border_focus']};
    }}

    QLineEdit:disabled {{
        color: {COLORS['text_muted']};
    }}

    QSpinBox, QDoubleSpinBox {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {COLORS['border_focus']};
    }}

    QComboBox {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QComboBox:focus {{
        border: 1px solid {COLORS['border_focus']};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        selection-background-color: {COLORS['bg_hover']};
    }}

    QTextEdit {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_secondary']};
        border: 1px solid {COLORS['border']};
        border-radius: 8px;
        padding: 10px;
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 13px;
    }}

    /* ─── Labels ─── */
    QLabel#titleLabel {{
        color: {COLORS['text_primary']};
        font-size: 26px;
        font-weight: 700;
    }}

    QLabel#subtitleLabel {{
        color: {COLORS['text_muted']};
        font-size: 13px;
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
        color: {COLORS['text_muted']};
        font-size: 11px;
        font-weight: 600;
        background-color: {COLORS['bg_tertiary']};
        border-radius: 4px;
        padding: 3px 8px;
    }}

    /* ─── ScrollArea ─── */
    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background-color: {COLORS['bg_primary']};
        width: 6px;
        border-radius: 3px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {COLORS['border']};
        border-radius: 3px;
        min-height: 30px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS['text_muted']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}

    QProgressBar {{
        background-color: {COLORS['bg_tertiary']};
        border: none;
        border-radius: 4px;
        height: 6px;
        color: transparent;
    }}

    QProgressBar::chunk {{
        background-color: {COLORS['text_primary']};
        border-radius: 4px;
    }}

    QToolTip {{
        background-color: {COLORS['bg_secondary']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border']};
        border-radius: 4px;
        padding: 5px 8px;
        font-size: 12px;
    }}
"""


CARD_BALANCE_STYLE = f"""
    background-color: {COLORS['bg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 16px;
    padding: 28px;
"""

ETH_ICON_STYLE = f"""
    color: {COLORS['text_secondary']};
    font-size: 32px;
    font-weight: 700;
"""
