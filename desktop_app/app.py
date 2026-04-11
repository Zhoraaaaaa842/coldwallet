"""
ColdVault ETH — Точка входа десктоп-приложения.
"""

import sys
import os

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from desktop_app.main_window import ColdVaultMainWindow


def main():
    # High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("ColdVault ETH")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ColdVault")

    # Шрифт по умолчанию
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = ColdVaultMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
