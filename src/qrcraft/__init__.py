"""QRCraft — Beautiful, animated QR codes with gradients, custom finders, and logo overlays."""

__version__ = "1.0.0"

from qrcraft.generator import (
    generate_qr_matrix,
    render_qr_image,
    overlay_logo,
    generate_animated_gif,
)

__all__ = [
    "generate_qr_matrix",
    "render_qr_image",
    "overlay_logo",
    "generate_animated_gif",
]
