"""
QR-коды для получения ETH:
- генерация QR с адресом (EIP-681)
- разбор входящего QR через OpenCV (без проблем с DLL на Windows)
"""

import re
from dataclasses import dataclass
from typing import Optional

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# Обратная совместимость: если pyzbar всё же установлен — используем его
HAS_PYZBAR = False
try:
    from pyzbar import pyzbar as _pyzbar
    HAS_PYZBAR = True
except Exception:
    pass


@dataclass
class QRPaymentRequest:
    """Разобранный платёжный запрос из QR."""
    address: str
    amount_eth: Optional[float] = None
    chain_id: Optional[int] = None
    label: Optional[str] = None
    raw: str = ""


# ─── Генерация QR ─── #

def generate_receive_qr(
    address: str,
    amount_eth: Optional[float] = None,
    chain_id: int = 1,
    label: str = "",
    size: int = 300,
):
    """
    Генерирует QR-код EIP-681.
    Возвращает PIL Image.
    """
    if not HAS_QRCODE or not HAS_PIL:
        raise ImportError("Установите: pip install qrcode[pil] Pillow")

    uri = _build_eip681_uri(address, amount_eth, chain_id, label)

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img = img.resize((size, size), PILImage.NEAREST)
    return img


def _build_eip681_uri(
    address: str,
    amount_eth: Optional[float],
    chain_id: int,
    label: str,
) -> str:
    uri = f"ethereum:{address}"
    if chain_id and chain_id != 1:
        uri += f"@{chain_id}"
    params = []
    if amount_eth and amount_eth > 0:
        wei = int(amount_eth * 10 ** 18)
        params.append(f"value={wei}")
    if label:
        params.append(f"label={label}")
    if params:
        uri += "?" + "&".join(params)
    return uri


# ─── Разбор QR URI ─── #

def parse_qr_uri(raw: str) -> QRPaymentRequest:
    """
    Разбирает строку из QR:
    - EIP-681: ethereum:0x...@1?value=...&label=...
    - Голый адрес: 0x...
    """
    raw = raw.strip()

    if re.fullmatch(r"0x[0-9a-fA-F]{40}", raw):
        return QRPaymentRequest(address=raw, raw=raw)

    m = re.match(
        r"ethereum:(?P<addr>0x[0-9a-fA-F]{40})"
        r"(?:@(?P<chain>\d+))?"
        r"(?:\?(?P<params>.*))?$",
        raw,
    )
    if not m:
        raise ValueError(f"Неизвестный формат QR: {raw!r}")

    address = m.group("addr")
    chain_id = int(m.group("chain")) if m.group("chain") else None
    params_str = m.group("params") or ""
    params = dict(p.split("=", 1) for p in params_str.split("&") if "=" in p)

    amount_eth: Optional[float] = None
    if "value" in params:
        try:
            amount_eth = int(params["value"]) / 10 ** 18
        except ValueError:
            pass

    return QRPaymentRequest(
        address=address,
        amount_eth=amount_eth,
        chain_id=chain_id,
        label=params.get("label"),
        raw=raw,
    )


# ─── Декодирование QR из файла ─── #

def decode_qr_from_image(image_path: str) -> str:
    """
    Декодирует QR из PNG/JPG.
    Сначала пробует OpenCV (работает без DLL на Windows),
    затем pyzbar как резерв.
    """
    # Приоритет 1: OpenCV
    if HAS_CV2:
        return _decode_with_cv2(image_path)

    # Приоритет 2: pyzbar (fallback)
    if HAS_PYZBAR and HAS_PIL:
        return _decode_with_pyzbar(image_path)

    raise ImportError(
        "Установите OpenCV:\n"
        "pip install opencv-python"
    )


def _decode_with_cv2(image_path: str) -> str:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Не удалось открыть файл: {image_path}")
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    if not data:
        raise ValueError("QR-код не найден в изображении")
    return data


def _decode_with_pyzbar(image_path: str) -> str:
    img = PILImage.open(image_path)
    decoded = _pyzbar.decode(img)
    if not decoded:
        raise ValueError("QR-код не найден в изображении")
    return decoded[0].data.decode("utf-8")
