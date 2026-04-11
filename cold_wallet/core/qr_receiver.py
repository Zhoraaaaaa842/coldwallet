"""
QR-коды для получения ETH:
- генерация QR с адресом (+ опциональная сумма)
- разбор входящего QR (EIP-681 / raw address)
"""

import re
from dataclasses import dataclass, field
from typing import Optional

try:
    import qrcode
    from qrcode.image.pil import PilImage
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pyzbar import pyzbar
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False


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
) -> Optional[object]:  # возвращает PIL Image или None
    """
    Генерирует QR-код с EIP-681 URI.
    ethereum:<address>[@<chainId>][?value=<wei>&label=<label>]
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
        wei = int(amount_eth * 10**18)
        params.append(f"value={wei}")
    if label:
        params.append(f"label={label}")
    if params:
        uri += "?" + "&".join(params)
    return uri


# ─── Разбор QR ─── #

def parse_qr_uri(raw: str) -> QRPaymentRequest:
    """
    Разбирает строку из QR. Поддерживает:
    - EIP-681: ethereum:0x...@1?value=1000000000000000000&label=Alice
    - Голый адрес: 0x...
    """
    raw = raw.strip()

    # Голый адрес
    if re.fullmatch(r"0x[0-9a-fA-F]{40}", raw):
        return QRPaymentRequest(address=raw, raw=raw)

    # EIP-681
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
            amount_eth = int(params["value"]) / 10**18
        except ValueError:
            pass

    return QRPaymentRequest(
        address=address,
        amount_eth=amount_eth,
        chain_id=chain_id,
        label=params.get("label"),
        raw=raw,
    )


def decode_qr_from_image(image_path: str) -> str:
    """
    Декодирует QR из файла изображения. Требует pyzbar + Pillow.
    Возвращает строку содержимого QR.
    """
    if not HAS_PYZBAR or not HAS_PIL:
        raise ImportError("Установите: pip install pyzbar Pillow")

    img = PILImage.open(image_path)
    decoded = pyzbar.decode(img)
    if not decoded:
        raise ValueError("QR-код не найден в изображении")
    return decoded[0].data.decode("utf-8")
