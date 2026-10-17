"""Generate Hourglass favicons: the original 21x21 pixel-art logo, untouched, centred on a coloured disc.

Usage (from web/, requires Pillow):
    python scripts/make_favicons.py app/static/icons/favicon.png app/static/icons
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

SRC = Path(sys.argv[1])          # original white pixel-art logo (21x21)
OUT = Path(sys.argv[2])          # web/app/static/icons
DISC = (88, 101, 242, 255)       # #5865F2
DISC_HEX = "#5865F2"

logo = Image.open(SRC).convert("RGBA")
glyph = logo.crop(logo.getbbox())  # drop the transparent padding only, the drawing is unchanged
gw, gh = glyph.size


def disc(size: int) -> Image.Image:
    """Anti-aliased full-bleed circle (drawn 4x larger then downsampled)."""
    big = Image.new("RGBA", (size * 4, size * 4), (0, 0, 0, 0))
    ImageDraw.Draw(big).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=DISC)
    return big.resize((size, size), Image.LANCZOS)


def render(size: int, scale: int) -> Image.Image:
    """Disc + logo scaled by an integer factor with nearest-neighbour, so pixels stay perfectly sharp."""
    img = disc(size)
    g = glyph.resize((gw * scale, gh * scale), Image.NEAREST)
    img.alpha_composite(g, ((size - g.width) // 2, (size - g.height) // 2))
    return img


# Integer scales chosen so the logo's corners stay inside the circle with a comfortable margin
master = render(512, 16)
sizes = {
    "favicon-32.png": render(32, 1),       # original pixels 1:1
    "apple-touch-icon.png": render(180, 6),
    "icon-192.png": render(192, 6),
    "icon-512.png": master,
}
for name, img in sizes.items():
    img.save(OUT / name, optimize=True)

# Multi-size .ico for /favicon.ico (Google & legacy clients); 48px is downsampled from the master
ico_48 = master.resize((48, 48), Image.LANCZOS)
ico_16 = render(32, 1).resize((16, 16), Image.LANCZOS)
ico_48.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)],
            append_images=[ico_16, render(32, 1)])

# Vector favicon: same pixels as crisp squares on a circle (sharp at any DPI)
rects = []
for y in range(gh):
    for x in range(gw):
        if glyph.getpixel((x, y))[3] > 128:
            rects.append(f'<rect x="{x}" y="{y}" width="1" height="1"/>')
# Whole-pixel offsets (same as the 32px PNG) so squares land on the pixel grid
pad_x = (32 - gw) // 2
pad_y = (32 - gh) // 2
svg = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    f'<circle cx="16" cy="16" r="16" fill="{DISC_HEX}"/>'
    f'<g fill="#ffffff" shape-rendering="crispEdges" transform="translate({pad_x} {pad_y})">'
    + "".join(rects)
    + "</g></svg>\n"
)
(OUT / "favicon.svg").write_text(svg, encoding="utf-8")
print("glyph", glyph.size, "->", ", ".join(sorted(list(sizes) + ["favicon.ico", "favicon.svg"])))
