"""Command-line interface for QRCraft."""

import argparse
import os

from qrcraft.generator import (
    ERROR_LEVELS,
    generate_animated_gif,
    generate_qr_matrix,
    hex_to_rgb,
    overlay_logo,
    render_qr_image,
)


def main():
    parser = argparse.ArgumentParser(
        prog="qrcraft",
        description="Generate beautiful, branded QR codes with gradients, custom finders, and animation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  qrcraft "https://example.com"
  qrcraft "https://example.com" --fg-color "#FF6600" --fg-color2 "#CC0066"
  qrcraft "https://example.com" --logo logo.png --output branded.png
  qrcraft "https://example.com" --animate --frames 36 --duration 3.0
  qrcraft "https://example.com" --no-gradient --no-fancy-finders --no-circle-modules
""",
    )
    parser.add_argument("url", help="URL or text to encode in the QR code")
    parser.add_argument(
        "-o", "--output", default="qr_output.png", help="Output file path (default: qr_output.png)"
    )

    colors = parser.add_argument_group("colors")
    colors.add_argument(
        "--fg-color", default="#1400FF", help="Primary module color as hex (default: #1400FF)"
    )
    colors.add_argument(
        "--fg-color2", default="#7B00FF", help="Secondary gradient color as hex (default: #7B00FF)"
    )
    colors.add_argument(
        "--bg-color", default="#FFFFFF", help="Background color as hex (default: #FFFFFF)"
    )

    logo_group = parser.add_argument_group("logo")
    logo_group.add_argument("--logo", default=None, help="Path to logo image")
    logo_group.add_argument(
        "--logo-scale", type=float, default=0.25, help="Logo size as fraction of QR (0.0-0.5, default: 0.25)"
    )
    logo_group.add_argument(
        "--logo-bg-color", default=None, help="Background behind logo as hex (default: same as --bg-color)"
    )
    logo_group.add_argument(
        "--logo-padding", type=int, default=10, help="Padding around logo in pixels (default: 10)"
    )
    logo_group.add_argument("--no-logo", action="store_true", help="Skip logo overlay")

    qr_params = parser.add_argument_group("qr parameters")
    qr_params.add_argument("--size", type=int, default=1000, help="Image size in pixels (default: 1000)")
    qr_params.add_argument("--border", type=int, default=2, help="Quiet zone in modules (default: 2)")
    qr_params.add_argument(
        "--error-correction",
        choices=["L", "M", "Q", "H"],
        default="H",
        help="Error correction level (default: H, recommended with logo)",
    )

    style = parser.add_argument_group("style")
    style.add_argument("--no-gradient", action="store_true", help="Disable gradient, use flat color")
    style.add_argument("--no-fancy-finders", action="store_true", help="Use standard square finder patterns")
    style.add_argument("--no-circle-modules", action="store_true", help="Use square modules instead of circles")
    style.add_argument("--rounded", action="store_true", help="Use rounded-rect modules (when circles disabled)")
    style.add_argument(
        "--round-radius", type=float, default=0.4, help="Corner radius fraction 0.0-0.5 (default: 0.4)"
    )

    anim = parser.add_argument_group("animation")
    anim.add_argument("--animate", action="store_true", help="Output animated GIF with rotating gradient")
    anim.add_argument("--frames", type=int, default=36, help="Number of frames (default: 36)")
    anim.add_argument("--duration", type=float, default=3.0, help="Loop duration in seconds (default: 3.0)")

    args = parser.parse_args()

    fg = hex_to_rgb(args.fg_color)
    fg2 = hex_to_rgb(args.fg_color2)
    bg = hex_to_rgb(args.bg_color)
    logo_bg = hex_to_rgb(args.logo_bg_color) if args.logo_bg_color else bg
    ec = ERROR_LEVELS[args.error_correction]
    use_gradient = not args.no_gradient
    fancy_finders = not args.no_fancy_finders
    circle_modules = not args.no_circle_modules

    print(f"URL:              {args.url}")
    print(f"FG color:         #{args.fg_color.lstrip('#').upper()}")
    if use_gradient:
        print(f"FG color2:        #{args.fg_color2.lstrip('#').upper()}")
    print(f"BG color:         #{args.bg_color.lstrip('#').upper()}")
    print(f"Size:             {args.size}px")
    print(f"Error correction: {args.error_correction}")
    print(f"Gradient:         {use_gradient}")
    print(f"Fancy finders:    {fancy_finders}")
    print(f"Circle modules:   {circle_modules}")

    # Generate QR matrix
    qr = generate_qr_matrix(args.url, error_correction=ec, border=args.border)
    matrix = qr.get_matrix()
    print(f"QR version:       {qr.version} ({len(matrix)}x{len(matrix)} modules)")

    if args.animate:
        output = args.output
        if not output.lower().endswith(".gif"):
            output = os.path.splitext(output)[0] + ".gif"
        print(f"Animate:          {args.frames} frames, {args.duration}s loop")
        logo = args.logo if not args.no_logo else None
        generate_animated_gif(
            qr,
            output_path=output,
            size=args.size,
            fg_color=fg,
            bg_color=bg,
            fg_color2=fg2,
            rounded=args.rounded,
            round_radius=args.round_radius,
            fancy_finders=fancy_finders,
            circle_modules=circle_modules,
            logo_path=logo,
            logo_scale=args.logo_scale,
            logo_bg_color=logo_bg,
            logo_padding=args.logo_padding,
            num_frames=args.frames,
            duration_seconds=args.duration,
        )
        print(f"\nSaved to: {os.path.abspath(output)}")
    else:
        img = render_qr_image(
            qr,
            size=args.size,
            fg_color=fg,
            bg_color=bg,
            fg_color2=fg2,
            rounded=args.rounded,
            round_radius=args.round_radius,
            use_gradient=use_gradient,
            fancy_finders=fancy_finders,
            circle_modules=circle_modules,
        )

        if not args.no_logo and args.logo:
            if not os.path.exists(args.logo):
                print(f"WARNING: Logo not found at {args.logo}, skipping overlay")
            else:
                print(f"Logo:             {args.logo}")
                print(f"Logo scale:       {args.logo_scale}")
                img = overlay_logo(
                    img,
                    logo_path=args.logo,
                    logo_scale=args.logo_scale,
                    logo_bg_color=logo_bg,
                    logo_padding=args.logo_padding,
                )

        img.save(args.output, "PNG")
        print(f"\nSaved to: {os.path.abspath(args.output)}")


if __name__ == "__main__":
    main()
