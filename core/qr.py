"""Inline SVG QR codes (docs/routes.md: "QR code ... as inline SVG").

SVG needs no imaging library — a PNG path would require Pillow, which is not a
dependency. Shared by the VIP invite page and the entry badges.
"""

from django.utils.safestring import mark_safe


def qr_svg(data: str) -> str:
    import qrcode
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(data, image_factory=SvgPathImage, border=0)
    # markup is generated here from our own token/URL, never from user input → safe
    return mark_safe(img.to_string(encoding="unicode"))
