"""
Runtime hook для PyInstaller.
Принудительно импортирует PIL и qrcode ДО запуска основного приложения,
чтобы PyInstaller включил их в бандл.
"""
import importlib

# Pillow — имя пакета PIL, но дистрибутив называется Pillow
# PyInstaller часто теряет его при --onefile
for mod in [
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "qrcode",
    "qrcode.constants",
    "qrcode.image",
    "qrcode.image.pil",
    "qrcode.image.base",
    "qrcode.main",
]:
    try:
        importlib.import_module(mod)
    except ImportError:
        pass
