import sys
from PyQt6.QtWidgets import QApplication
from desktop_app.main_window import ColdVaultMainWindow

BANNER = r"""
 ____  _
|_  / | |_   ___   _ _   __ _   __ _   __ _   __ _
 / /  | ' \ / _ \ | '_| / _` | / _` | / _` | / _` |
/___|  |_||_|\___/ |_|   \__,_| \__,_| \__,_| \__,_|

          ZhoraaaaAA  Cold  Wallet  v1.0.0
          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

if __name__ == "__main__":
    print(BANNER)
    app = QApplication(sys.argv)
    window = ColdVaultMainWindow()
    window.show()
    sys.exit(app.exec())
