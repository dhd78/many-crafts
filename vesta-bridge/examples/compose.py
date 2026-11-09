"""Side-by-side comparison helper.

The example figures are reproductions of figures from published theses; those
original figures are copyrighted and are **not** included in this repository.
If you have your own reference image, use this script to put it next to a
render produced by the VESTA bridge.

Usage:
    python compose.py --left reference.png --right out-slab-side4.png --out comparison.png
"""

import argparse

from PIL import Image, ImageDraw, ImageFont


def load(path, height):
    image = Image.open(path).convert("RGB")
    width = int(image.width * height / image.height)
    return image.resize((width, height), Image.LANCZOS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compose two images side by side")
    parser.add_argument("--left", required=True, help="left image (e.g. your reference figure)")
    parser.add_argument("--right", required=True, help="right image (e.g. a VESTA render)")
    parser.add_argument("--out", required=True, help="output PNG")
    parser.add_argument("--left-label", default="reference")
    parser.add_argument("--right-label", default="VESTA render")
    parser.add_argument("--height", type=int, default=900, help="panel height in pixels")
    args = parser.parse_args()

    left = load(args.left, args.height)
    right = load(args.right, args.height)

    pad = 24
    head = 36
    width = left.width + right.width + pad * 3
    canvas = Image.new("RGB", (width, args.height + head + pad), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    except OSError:
        font = ImageFont.load_default()

    draw.text((pad, 8), args.left_label, fill="black", font=font)
    draw.text((pad * 2 + left.width, 8), args.right_label, fill="black", font=font)
    canvas.paste(left, (pad, head))
    canvas.paste(right, (pad * 2 + left.width, head))
    canvas.save(args.out)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
