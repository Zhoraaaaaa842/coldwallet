"""
Runtime hook для PyInstaller.
Принудительно импортирует PIL и qrcode ДО запуска основного приложения.
Ошибки НЕ глотаются — это важно для диагностики проблем сборки.
"""
import sys
import os

# Убеждаемся, что папка _MEIPASS (распакованный бандл) в sys.path
if hasattr(sys, '_MEIPASS'):
    meipass = sys._MEIPASS
    if meipass not in sys.path:
        sys.path.insert(0, meipass)
    # PIL хранит бинарные .libs в _MEIPASS/PIL/.libs — добавляем в PATH
    pil_libs = os.path.join(meipass, "PIL", ".libs")
    if os.path.isdir(pil_libs):
        os.environ["PATH"] = pil_libs + os.pathsep + os.environ.get("PATH", "")

# Принудительный импорт — без try/except чтобы сразу видеть ошибку
import PIL
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import qrcode
import qrcode.constants
import qrcode.image
import qrcode.image.pil
import qrcode.image.base
import qrcode.main
