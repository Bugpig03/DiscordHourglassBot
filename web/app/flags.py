"""Pixel-art flags of the site languages, drawn on a 15 x 10 grid like the pixel icons.

Each flag is a list of 10 rows of 15 letters; every letter is a color of that flag's palette.
flag_svg() turns a grid into an SVG with one path per color (one rectangle per run of pixels).
"""
from functools import lru_cache

from markupsafe import Markup

W, H = 15, 10


def _bands(colors: str, sizes: list[int], vertical: bool = False) -> list[str]:
    """Horizontal (or vertical) stripes: colors[i] repeated sizes[i] rows (or columns)."""
    line = "".join(c * n for c, n in zip(colors, sizes))
    if vertical:
        return [line] * H
    return [c * W for c, n in zip(colors, sizes) for _ in range(n)]


def _paint(grid: list[str], color: str, test) -> list[str]:
    """Return the grid with every pixel whose center passes test(x, y) painted in color."""
    return ["".join(color if test(x + 0.5, y + 0.5) else c for x, c in enumerate(row)) for y, row in enumerate(grid)]


def _uk() -> list[str]:
    rows = []
    for y in range(H):
        row = ""
        for x in range(W):
            cx, cy = x + 0.5, y + 0.5
            d1 = abs(cy - cx * H / W)
            d2 = abs(cy - (W - cx) * H / W)
            c = "B"
            if min(d1, d2) < 1.0:
                c = "W"
            if min(d1, d2) < 0.4:
                c = "R"
            if 6 <= x <= 8 or 3 <= y <= 6:
                c = "W"
            if x == 7 or y in (4, 5):
                c = "R"
            row += c
        rows.append(row)
    return rows


def _spain() -> list[str]:
    g = _bands("RYR", [2, 6, 2])
    return _paint(g, "D", lambda x, y: 3 <= x <= 5 and 4 <= y <= 6)


def _brazil() -> list[str]:
    g = _paint(["G" * W] * H, "Y", lambda x, y: abs(x - 7.5) / 6.6 + abs(y - 5) / 4.4 <= 1)
    return _paint(g, "B", lambda x, y: (x - 7.5) ** 2 + (y - 5) ** 2 <= 2.4 ** 2)


def _turkey() -> list[str]:
    g = _paint(["R" * W] * H, "W", lambda x, y: (x - 5.6) ** 2 + (y - 5) ** 2 <= 3.1 ** 2)
    g = _paint(g, "R", lambda x, y: (x - 6.5) ** 2 + (y - 5) ** 2 <= 2.4 ** 2)
    star = {(9, 4), (9, 5), (10, 4), (10, 5), (8, 4), (11, 5), (9, 3), (10, 6)}
    return _paint(g, "W", lambda x, y: (int(x), int(y)) in star)


def _india() -> list[str]:
    g = _bands("OWG", [3, 4, 3])
    wheel = {(7, 3), (6, 4), (8, 4), (6, 5), (8, 5), (7, 6)}  # Ashoka chakra as a small ring
    return _paint(g, "N", lambda x, y: (int(x), int(y)) in wheel)


def _japan() -> list[str]:
    return _paint(["W" * W] * H, "R", lambda x, y: (x - 7.5) ** 2 + (y - 5) ** 2 <= 2.9 ** 2)


def _korea() -> list[str]:
    in_circle = lambda x, y: (x - 7.5) ** 2 + (y - 5) ** 2 <= 2.9 ** 2  # noqa: E731
    g = _paint(["W" * W] * H, "R", lambda x, y: in_circle(x, y) and y < 5)
    g = _paint(g, "B", lambda x, y: in_circle(x, y) and y >= 5)
    bars = {(1, 1), (2, 1), (2, 2), (12, 1), (13, 1), (12, 2), (1, 8), (2, 8), (2, 7), (12, 8), (13, 8), (12, 7)}
    return _paint(g, "K", lambda x, y: (int(x), int(y)) in bars)


FLAGS = {
    "fr": (_bands("BWR", [5, 5, 5], vertical=True), {"B": "#002654", "W": "#FFFFFF", "R": "#CE1126"}),
    "en": (_uk(), {"B": "#012169", "W": "#FFFFFF", "R": "#C8102E"}),
    "es": (_spain(), {"R": "#AA151B", "Y": "#F1BF00", "D": "#AD1519"}),
    "pt": (_brazil(), {"G": "#009C3B", "Y": "#FFDF00", "B": "#002776"}),
    "it": (_bands("GWR", [5, 5, 5], vertical=True), {"G": "#009246", "W": "#FFFFFF", "R": "#CE2B37"}),
    "de": (_bands("KRY", [3, 4, 3]), {"K": "#000000", "R": "#DD0000", "Y": "#FFCE00"}),
    "pl": (_bands("WR", [5, 5]), {"W": "#FFFFFF", "R": "#DC143C"}),
    "tr": (_turkey(), {"R": "#E30A17", "W": "#FFFFFF"}),
    "ru": (_bands("WBR", [3, 4, 3]), {"W": "#FFFFFF", "B": "#0039A6", "R": "#D52B1E"}),
    "hi": (_india(), {"O": "#FF9933", "W": "#FFFFFF", "G": "#138808", "N": "#000080"}),
    "ja": (_japan(), {"W": "#FFFFFF", "R": "#BC002D"}),
    "ko": (_korea(), {"W": "#FFFFFF", "R": "#CD2E3A", "B": "#0047A0", "K": "#000000"}),
}


@lru_cache(maxsize=None)
def flag_svg(code: str, cls: str = "lang-flag") -> Markup:
    """SVG markup of a language flag (15 x 10 pixels, crisp edges)."""
    grid, colors = FLAGS.get(code, FLAGS["en"])
    paths = []
    for letter, color in colors.items():
        d = []
        for y, row in enumerate(grid):
            x = 0
            while x < W:
                if row[x] != letter:
                    x += 1
                    continue
                start = x
                while x < W and row[x] == letter:
                    x += 1
                d.append(f"M{start} {y}h{x - start}v1h-{x - start}z")
        if d:
            paths.append(f'<path fill="{color}" d="{"".join(d)}"/>')
    return Markup(
        f'<svg class="{cls}" viewBox="0 0 {W} {H}" width="15" height="10" shape-rendering="crispEdges" aria-hidden="true">'
        + "".join(paths) + "</svg>"
    )
