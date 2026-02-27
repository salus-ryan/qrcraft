"""Core QR code generation engine."""

import math
import os

import qrcode
from qrcode.constants import (
    ERROR_CORRECT_H,
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
)
from PIL import Image, ImageDraw

ERROR_LEVELS = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: #{hex_color}")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def generate_qr_matrix(
    url: str,
    error_correction: int = ERROR_CORRECT_H,
    border: int = 2,
) -> qrcode.QRCode:
    """Generate a deterministic QR code matrix.

    Args:
        url: The data to encode in the QR code.
        error_correction: Error correction level (ERROR_CORRECT_L/M/Q/H).
        border: Quiet zone border width in modules.

    Returns:
        A qrcode.QRCode object with the matrix populated.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=error_correction,
        box_size=1,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr


def _lerp_color(
    c1: tuple[int, int, int],
    c2: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Linearly interpolate between two RGB colors. t in [0, 1]."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _is_finder_module(row: int, col: int, n: int, border: int) -> bool:
    """Check if a module is part of one of the three finder patterns."""
    finders = [
        (border, border),
        (border, n - 7 - border),
        (n - 7 - border, border),
    ]
    for fr, fc in finders:
        if fr <= row < fr + 7 and fc <= col < fc + 7:
            return True
    return False


def _draw_finder_pattern(
    draw: ImageDraw.Draw,
    cx: float,
    cy: float,
    outer_size: float,
    fg_color: tuple[int, int, int],
    bg_color: tuple[int, int, int],
) -> None:
    """Draw a custom rounded finder pattern centered at (cx, cy)."""
    # Outer rounded square
    r_outer = outer_size / 2
    radius_outer = outer_size * 0.25
    draw.rounded_rectangle(
        [cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer],
        radius=radius_outer,
        fill=(*fg_color, 255),
    )
    # Middle gap (white)
    r_mid = outer_size * 0.36
    radius_mid = outer_size * 0.18
    draw.rounded_rectangle(
        [cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid],
        radius=radius_mid,
        fill=(*bg_color, 255),
    )
    # Inner dot (circle)
    r_inner = outer_size * 0.21
    draw.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        fill=(*fg_color, 255),
    )


def render_qr_image(
    qr: qrcode.QRCode,
    size: int = 1000,
    fg_color: tuple[int, int, int] = (20, 0, 255),
    bg_color: tuple[int, int, int] = (255, 255, 255),
    fg_color2: tuple[int, int, int] | None = None,
    rounded: bool = False,
    round_radius: float = 0.4,
    use_gradient: bool = True,
    fancy_finders: bool = True,
    circle_modules: bool = True,
    gradient_angle: float = 45.0,
) -> Image.Image:
    """Render a QR matrix to a PIL Image.

    Args:
        qr: A populated qrcode.QRCode object.
        size: Output image size in pixels (square).
        fg_color: Primary foreground RGB color.
        bg_color: Background RGB color.
        fg_color2: Secondary color for gradient. If None, uses fg_color.
        rounded: Use rounded rectangles for modules (when circle_modules=False).
        round_radius: Corner radius fraction for rounded modules (0.0-0.5).
        use_gradient: Apply gradient across modules.
        fancy_finders: Use custom rounded finder patterns.
        circle_modules: Use circular modules instead of squares.
        gradient_angle: Gradient direction in degrees (0=left-to-right, 90=top-to-bottom).

    Returns:
        A PIL RGBA Image of the rendered QR code.
    """
    matrix = qr.get_matrix()
    modules = len(matrix)
    box_size = size / modules
    border = qr.border

    if fg_color2 is None:
        fg_color2 = fg_color

    img = Image.new("RGBA", (size, size), (*bg_color, 255))
    draw = ImageDraw.Draw(img)

    # --- Draw data modules (skip finder regions) ---
    for row_idx, row in enumerate(matrix):
        for col_idx, module in enumerate(row):
            if not module:
                continue
            if fancy_finders and _is_finder_module(row_idx, col_idx, modules, border):
                continue

            x0 = col_idx * box_size
            y0 = row_idx * box_size
            x1 = x0 + box_size
            y1 = y0 + box_size
            cx = (x0 + x1) / 2
            cy = (y0 + y1) / 2

            # Gradient: interpolate color based on angle-rotated position
            if use_gradient and fg_color != fg_color2:
                nx = col_idx / modules - 0.5
                ny = row_idx / modules - 0.5
                angle_rad = math.radians(gradient_angle)
                proj = nx * math.cos(angle_rad) + ny * math.sin(angle_rad)
                t = proj + 0.5
                t = max(0.0, min(1.0, t))
                color = _lerp_color(fg_color, fg_color2, t)
            else:
                color = fg_color

            if circle_modules:
                r = box_size * 0.42
                draw.ellipse(
                    [cx - r, cy - r, cx + r, cy + r],
                    fill=(*color, 255),
                )
            elif rounded:
                radius = box_size * round_radius
                draw.rounded_rectangle(
                    [x0, y0, x1, y1],
                    radius=radius,
                    fill=(*color, 255),
                )
            else:
                draw.rectangle([x0, y0, x1, y1], fill=(*color, 255))

    # --- Draw custom finder patterns ---
    if fancy_finders:
        finder_positions = [
            (border + 3.5, border + 3.5),
            (border + 3.5, modules - border - 3.5),
            (modules - border - 3.5, border + 3.5),
        ]
        finder_size = box_size * 7
        for fr, fc in finder_positions:
            cx = fc * box_size
            cy = fr * box_size
            if use_gradient and fg_color != fg_color2:
                nx = fc / modules - 0.5
                ny = fr / modules - 0.5
                angle_rad = math.radians(gradient_angle)
                proj = nx * math.cos(angle_rad) + ny * math.sin(angle_rad)
                t = proj + 0.5
                t = max(0.0, min(1.0, t))
                color = _lerp_color(fg_color, fg_color2, t)
            else:
                color = fg_color
            _draw_finder_pattern(draw, cx, cy, finder_size, color, bg_color)

    return img


def overlay_logo(
    qr_img: Image.Image,
    logo_path: str,
    logo_scale: float = 0.25,
    logo_bg_color: tuple[int, int, int] = (255, 255, 255),
    logo_padding: int = 10,
) -> Image.Image:
    """Overlay a logo in the center of a QR code image.

    Args:
        qr_img: The QR code image to overlay on.
        logo_path: Path to the logo image file.
        logo_scale: Logo size as fraction of QR code (0.0-0.5).
        logo_bg_color: Background color behind the logo.
        logo_padding: Padding around the logo in pixels.

    Returns:
        A new PIL Image with the logo overlaid.
    """
    logo = Image.open(logo_path).convert("RGBA")

    qr_size = qr_img.size[0]
    max_logo_size = int(qr_size * logo_scale)

    # Scale logo preserving aspect ratio
    logo_ratio = logo.width / logo.height
    if logo_ratio >= 1:
        new_w = max_logo_size
        new_h = int(max_logo_size / logo_ratio)
    else:
        new_h = max_logo_size
        new_w = int(max_logo_size * logo_ratio)

    logo = logo.resize((new_w, new_h), Image.LANCZOS)

    # Create background rectangle behind logo
    bg_w = new_w + logo_padding * 2
    bg_h = new_h + logo_padding * 2
    bg_x = (qr_size - bg_w) // 2
    bg_y = (qr_size - bg_h) // 2

    result = qr_img.copy()
    draw = ImageDraw.Draw(result)
    draw.rounded_rectangle(
        [bg_x, bg_y, bg_x + bg_w, bg_y + bg_h],
        radius=logo_padding,
        fill=(*logo_bg_color, 255),
    )

    # Paste logo centered
    logo_x = (qr_size - new_w) // 2
    logo_y = (qr_size - new_h) // 2
    result.paste(logo, (logo_x, logo_y), logo)

    return result


def generate_animated_gif(
    qr: qrcode.QRCode,
    output_path: str,
    size: int = 1000,
    fg_color: tuple[int, int, int] = (20, 0, 255),
    bg_color: tuple[int, int, int] = (255, 255, 255),
    fg_color2: tuple[int, int, int] = (123, 0, 255),
    rounded: bool = False,
    round_radius: float = 0.4,
    fancy_finders: bool = True,
    circle_modules: bool = True,
    logo_path: str | None = None,
    logo_scale: float = 0.25,
    logo_bg_color: tuple[int, int, int] = (255, 255, 255),
    logo_padding: int = 10,
    num_frames: int = 36,
    duration_seconds: float = 3.0,
) -> None:
    """Generate an animated GIF with the gradient rotating 360 degrees.

    Each frame is an independently scannable QR code. Only the gradient
    angle changes between frames — module positions are fixed.

    Args:
        qr: A populated qrcode.QRCode object.
        output_path: Path to write the GIF file.
        size: Image size in pixels.
        fg_color: Primary gradient color.
        bg_color: Background color.
        fg_color2: Secondary gradient color.
        rounded: Use rounded rectangles (when circle_modules=False).
        round_radius: Corner radius fraction.
        fancy_finders: Use custom rounded finder patterns.
        circle_modules: Use circular modules.
        logo_path: Path to logo image, or None to skip.
        logo_scale: Logo size as fraction of QR code.
        logo_bg_color: Background color behind logo.
        logo_padding: Padding around logo in pixels.
        num_frames: Number of frames in the animation.
        duration_seconds: Total loop duration in seconds.
    """
    frames = []
    frame_duration_ms = int((duration_seconds / num_frames) * 1000)

    for i in range(num_frames):
        angle = (360.0 / num_frames) * i
        print(f"  Rendering frame {i + 1}/{num_frames} (angle={angle:.0f}\u00b0)", end="\r")

        frame = render_qr_image(
            qr,
            size=size,
            fg_color=fg_color,
            bg_color=bg_color,
            fg_color2=fg_color2,
            rounded=rounded,
            round_radius=round_radius,
            use_gradient=True,
            fancy_finders=fancy_finders,
            circle_modules=circle_modules,
            gradient_angle=angle,
        )

        if logo_path and os.path.exists(logo_path):
            frame = overlay_logo(
                frame,
                logo_path=logo_path,
                logo_scale=logo_scale,
                logo_bg_color=logo_bg_color,
                logo_padding=logo_padding,
            )

        # Convert RGBA to RGB for GIF
        rgb_frame = Image.new("RGB", frame.size, (*bg_color,))
        rgb_frame.paste(frame, mask=frame.split()[3])
        frames.append(rgb_frame)

    print()

    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=frame_duration_ms,
        loop=0,
        optimize=True,
    )
