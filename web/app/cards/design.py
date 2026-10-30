"""Design system of the stat cards, in the website's "Arène" style: colors, fonts, cut-corner shapes, pixel icons,
images and PNG export.

Cards are meant to be read at small size (a Discord image is usually seen without clicking, around
500 px wide): they are drawn on a large canvas (1200 px wide) with big type, then shown at half size
as SVG or exported as a sharp 2x PNG. No text should be smaller than ~24 px on the canvas.

Fonts are the website's own (Chakra Petch for titles, figures and captions, IBM Plex Sans for text, renamed HG Sans because "Plex" is a Reserved Font Name), converted
to TTF for resvg; Inter stays as the fallback that draws Cyrillic.
"""

import base64
import html
import io
import logging
import os
import threading
import time
from functools import lru_cache

import requests
from PIL import Image, ImageFont, ImageOps

from app.i18n import day_month_year, format_number
from app.pixel_icons import INNER as PIXEL_INNER, VIEWBOXES as PIXEL_VIEWBOXES

log = logging.getLogger(__name__)

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
DISPLAY = "'Chakra Petch', Inter, sans-serif"
BODY = "'HG Sans', Inter, sans-serif"
_FILES = {
    ("display", 500, False): "ChakraPetch-500.ttf",
    ("display", 600, False): "ChakraPetch-600.ttf",
    ("display", 700, False): "ChakraPetch-700.ttf",
    ("display", 600, True): "ChakraPetch-600Italic.ttf",
    ("display", 700, True): "ChakraPetch-700Italic.ttf",
    ("body", 400, False): "HGSans-400.ttf",
    ("body", 600, False): "HGSans-600.ttf",
    ("body", 700, False): "HGSans-700.ttf",
    ("inter", 400, False): "Inter-Regular.ttf",
    ("inter", 600, False): "Inter-SemiBold.ttf",
    ("inter", 700, False): "Inter-Bold.ttf",
}

# Website palette (static/css/arene.css)
BG = "#15161a"
BG_2 = "#1a1c21"
PANEL = "#212329"
PANEL_2 = "#292c33"
LINE = "#2e3138"
TEXT = "#f2f3f5"
SOFT = "#c9ccd3"
MUTED = "#a3a6b0"
DIM = "#72767d"
ACCENT = "#717cf8"
# One color per kind of figure, as on the website
VOICE = "#717cf8"
MESSAGES = "#3fd1a0"
XP = "#f5b03b"
SERVER = "#ff6b5e"
MEMBER = "#b07cff"
GOLD = "#f5c542"
SILVER = "#c9ced6"
BRONZE = "#d08a4f"
DANGER = "#ed4245"
SITE = "hourglassbot.net"
HOLO = "url(#holo)"   # Mythic badge tier: the rainbow gradient defined by document()

CUT = 24       # corner cut of the panels (12 px on the website, the canvas is 2x)
CUT_S = 12     # small elements (6 px on the website)


# ---------------------------------------------------------------------------
# Text: measured with the same files resvg draws with
# ---------------------------------------------------------------------------
def _weight(font: str, weight: int) -> int:
    if font == "display":
        return 500 if weight <= 500 else 600 if weight <= 600 else 700
    return 400 if weight <= 400 else 600 if weight <= 600 else 700


@lru_cache(maxsize=128)
def _font(font: str, weight: int, italic: bool, size: int) -> ImageFont.FreeTypeFont:
    key = (font, _weight(font, weight), italic and font == "display" and weight >= 600)
    return ImageFont.truetype(os.path.join(FONT_DIR, _FILES.get(key) or _FILES[(font, key[1], False)]), size)


@lru_cache(maxsize=8)
def _codepoints(name: str) -> frozenset:
    from fontTools.ttLib import TTFont
    with TTFont(os.path.join(FONT_DIR, name), lazy=True) as font:
        return frozenset(font.getBestCmap())


def _drawable() -> frozenset:
    return _codepoints(_FILES[("display", 700, False)]) | _codepoints(_FILES[("body", 400, False)]) | _codepoints(_FILES[("inter", 700, False)])


def clean(value) -> str:
    """Drop what no card font can draw (emoji, CJK...) instead of showing empty boxes; collapse the spaces left."""
    # Chakra Petch has no narrow no-break space (French thousands): a regular no-break space reads the same
    raw = str(value if value is not None else "").replace("\u202f", "\u00a0")
    codepoints = _drawable()
    kept = "".join(ch for ch in raw if ch.isspace() or ord(ch) in codepoints)
    return " ".join(kept.split()) if kept != raw else raw


def text_width(value: str, size: float, weight: int = 700, font: str = "display", italic: bool = False) -> float:
    """Width in canvas pixels (measured at 4x for sub-pixel precision); letters the font lacks are measured with Inter."""
    value = clean(value)
    own = _codepoints(_FILES[(font, _weight(font, weight), False)])
    if any(not ch.isspace() and ord(ch) not in own for ch in value):
        font, italic = "inter", False
    return _font(font, weight, italic, max(1, round(size * 4))).getlength(value) / 4


def fit_text(value: str, max_width: float, size: float, weight: int = 700, min_size: float | None = None,
             font: str = "display", italic: bool = False, spacing: float = 0) -> tuple[str, float]:
    """Shrink the font down to min_size, then shorten with an ellipsis, so the text fits max_width."""
    value = clean(value)
    min_size = min_size or size

    def width(v, s):
        return text_width(v, s, weight, font, italic) + spacing * len(v)

    while size > min_size and width(value, size) > max_width:
        size -= 1
    if width(value, size) <= max_width:
        return value, size
    while len(value) > 1 and width(value + "…", size) > max_width:
        value = value[:-1]
    return value.rstrip() + "…", size


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def text(x: float, y: float, value: str, size: float, weight: int = 700, fill: str = TEXT, anchor: str = "start",
         opacity: float | None = None, spacing: float | None = None, font: str = "display", italic: bool = False) -> str:
    family = DISPLAY if font == "display" else BODY
    extra = f' fill-opacity="{opacity}"' if opacity is not None else ""
    if spacing:
        extra += f' letter-spacing="{spacing}"'
    if italic:
        extra += ' font-style="italic"'
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size:.1f}" '
            f'font-weight="{_weight(font, weight)}" fill="{fill}" text-anchor="{anchor}"{extra}>{esc(clean(value))}</text>')


def caption(x: float, y: float, value: str, size: float = 23, fill: str = MUTED, anchor: str = "start") -> str:
    """Small uppercase caption above a value (Chakra Petch, spaced like the website's labels)."""
    return text(x, y, value.upper(), size, 600, fill, anchor, spacing=size * 0.08)


def caption_width(value: str, size: float) -> float:
    return text_width(value.upper(), size, 600) + size * 0.08 * len(value)


def ghost(x: float, y: float, value: str, size: float, anchor: str = "end", opacity: float = 0.08) -> str:
    """Huge outlined figure in the background (rank, level), like the website's titles."""
    family = DISPLAY
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size:.1f}" font-weight="700" font-style="italic" '
            f'fill="none" stroke="{TEXT}" stroke-opacity="{opacity}" stroke-width="3" text-anchor="{anchor}">{esc(clean(value))}</text>')


# ---------------------------------------------------------------------------
# Shapes: cut corners (top left and bottom right), slanted tags
# ---------------------------------------------------------------------------
def cut_points(x: float, y: float, w: float, h: float, c: float) -> str:
    c = min(c, w / 2, h / 2)
    pts = [(x + c, y), (x + w, y), (x + w, y + h - c), (x + w - c, y + h), (x, y + h), (x, y + c)]
    return " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)


def shape(x: float, y: float, w: float, h: float, fill: str, opacity: float = 1, cut: float = CUT,
          stroke: str | None = None, stroke_opacity: float = 1, stroke_width: float = 2) -> str:
    """Cut-corner box; the outline runs along the diagonals too, as on the website."""
    out = f'<polygon points="{cut_points(x, y, max(0, w), max(0, h), cut)}" fill="{fill}"'
    if opacity != 1:
        out += f' fill-opacity="{opacity}"'
    if stroke:
        out += f' stroke="{stroke}" stroke-opacity="{stroke_opacity}" stroke-width="{stroke_width}" stroke-linejoin="miter"'
    return out + "/>"


def panel(x: float, y: float, w: float, h: float, cut: float = CUT, fill: str = PANEL, stroke: str = LINE) -> str:
    """Card surface of the website (an-card): solid panel, thin line around, cut corners."""
    return shape(x, y, w, h, fill, 1, cut, stroke, 1, 2)


def top_line(x: float, y: float, w: float, cut: float, color: str, width: float = 5) -> str:
    """Colored top edge of a tile that carries on into the cut corner (the website's key figure tiles)."""
    half = width / 2
    return (f'<polyline points="{x + half:.1f},{y + cut:.1f} {x + cut:.1f},{y + half:.1f} {x + w - half:.1f},{y + half:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="miter"/>')


def slant(x: float, y: float, w: float, h: float, fill: str, opacity: float = 1, s: float = CUT_S,
          stroke: str | None = None, stroke_opacity: float = 1) -> str:
    pts = f"{x + s:.1f},{y:.1f} {x + w:.1f},{y:.1f} {x + w - s:.1f},{y + h:.1f} {x:.1f},{y + h:.1f}"
    out = f'<polygon points="{pts}" fill="{fill}"'
    if opacity != 1:
        out += f' fill-opacity="{opacity}"'
    if stroke:
        out += f' stroke="{stroke}" stroke-opacity="{stroke_opacity}" stroke-width="2"'
    return out + "/>"


def tag(x: float, y: float, value: str, color: str, size: float = 24, h: float = 46, anchor: str = "start",
        max_width: float | None = None, solid: bool = False) -> tuple[str, float]:
    """Slanted label (level, scope, period): tinted, or solid with dark text. Returns (svg, width)."""
    pad = h * 0.5
    spacing = size * 0.06
    value = value.upper()
    if max_width:
        value, size = fit_text(value, max_width - 2 * pad, size, 700, size * 0.8, spacing=spacing)
    w = text_width(value, size, 700) + spacing * len(value) + 2 * pad
    left = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
    if solid:
        svg = slant(left, y, w, h, color) + text(left + w / 2, y + h / 2 + size * 0.36, value, size, 700, BG, "middle", spacing=spacing)
    else:
        svg = (slant(left, y, w, h, color, 0.14, stroke=color, stroke_opacity=0.55)
               + text(left + w / 2, y + h / 2 + size * 0.36, value, size, 700, color, "middle", spacing=spacing))
    return svg, w


def progress(x: float, y: float, w: float, h: float, ratio: float, color: str) -> str:
    """Straight bar on a dark track (no rounded ends in the Arène style)."""
    ratio = max(0.0, min(1.0, ratio))
    fill_w = w * ratio
    out = f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{PANEL_2}"/>'
    if fill_w > 0:
        out += f'<rect x="{x:.1f}" y="{y:.1f}" width="{fill_w:.1f}" height="{h:.1f}" fill="{color}"/>'
    return out


def pixel(name: str, x: float, y: float, size: float, color: str) -> str:
    """Pixel-art icon of the website (9 x 9 grid), drawn crisp at any size."""
    inner = PIXEL_INNER.get(name) or PIXEL_INNER["star"]
    view = PIXEL_VIEWBOXES.get(name) or "0 0 9 9"
    return (f'<svg x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" viewBox="{view}" shape-rendering="crispEdges">'
            f'<g fill="{color}">{inner}</g></svg>')


def icon_block(x: float, y: float, size: float, name: str, color: str) -> str:
    """Icon on a solid square of its color (the website's tile icons)."""
    pad = size * 0.2
    return shape(x, y, size, size, color, 1, CUT_S * 0.75) + pixel(name, x + pad, y + pad, size - 2 * pad, BG)


# ---------------------------------------------------------------------------
# Numbers, dates and colors (in the card's language)
# ---------------------------------------------------------------------------
def fmt_int(n, lang: str = "en") -> str:
    return format_number(int(n or 0), 0, lang)


def fmt_hours(seconds, lang: str = "en") -> str:
    """Voice time: 35m, 45.2h, 771h, 12,450h (separators of the card's language)."""
    seconds = int(seconds or 0)
    if seconds < 3600:
        return f"{seconds // 60}m"
    hours = seconds / 3600
    return f"{format_number(hours, 1, lang)}h" if hours < 100 else f"{format_number(int(hours), 0, lang)}h"


def fmt_date(value, lang: str = "en") -> str:
    if not value:
        return "—"
    label = day_month_year(value.day, value.month, value.year, lang)
    return label.lower() if lang == "fr" else label   # "28 avr 2024", as on the website


def hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or ACCENT).lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def color_distance(a: str, b: str) -> float:
    (r1, g1, b1), (r2, g2, b2) = hex_rgb(a), hex_rgb(b)
    return ((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2) ** 0.5


# ---------------------------------------------------------------------------
# Images, embedded as data URIs (an SVG card must be self-contained)
# ---------------------------------------------------------------------------
_IMAGE_CACHE: dict[tuple, tuple[float, str | None]] = {}
_IMAGE_LOCK = threading.Lock()
_IMAGE_TTL, _IMAGE_FAIL_TTL, _IMAGE_CACHE_MAX = 3600, 300, 400


def _data_uri(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(buf, "JPEG", quality=86, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, "PNG", optimize=True)
        mime = "image/png"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


def _cached(key: tuple, build) -> str | None:
    now = time.time()
    with _IMAGE_LOCK:
        hit = _IMAGE_CACHE.get(key)
        if hit and now < hit[0]:
            return hit[1]
    try:
        value = build()
    except Exception as e:  # network error, unreadable image: the card falls back to initials
        log.info("Card image unavailable %s: %s", key[1], e)
        value = None
    with _IMAGE_LOCK:
        if len(_IMAGE_CACHE) >= _IMAGE_CACHE_MAX:
            _IMAGE_CACHE.clear()
        _IMAGE_CACHE[key] = (now + (_IMAGE_TTL if value else _IMAGE_FAIL_TTL), value)
    return value


def remote_square(url: str | None, size: int) -> str | None:
    """Avatar or server icon (Discord CDN), cropped square and resized to size x size."""
    if not url:
        return None
    if "cdn.discordapp.com" in url:
        url = url.replace(".webp", ".png").split("?")[0] + f"?size={256 if size <= 256 else 512}"

    def build():
        resp = requests.get(url, timeout=2.5)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content))
        img.seek(0)  # animated avatars: first frame
        return _data_uri(ImageOps.fit(img.convert("RGBA"), (size, size), Image.LANCZOS))

    return _cached(("remote", url, size), build)


def local_cover(path: str, w: int, h: int) -> str | None:
    """Local picture (gallery banner) cropped to cover w x h."""
    def build():
        with Image.open(path) as img:
            return _data_uri(ImageOps.fit(img.convert("RGB"), (w, h), Image.LANCZOS), "JPEG")

    return _cached(("local", path, w, h), build)


def _initial(name: str) -> str:
    return (clean(name) or "?").strip()[:1].upper() or "?"


def avatar(cx: float, cy: float, r: float, image_uri: str | None, name: str, ring: str, uid: str, ring_width: float = 6) -> str:
    """Round member avatar with a colored ring (avatars stay round on the website); the initial without a picture."""
    out = f'<circle cx="{cx}" cy="{cy}" r="{r + ring_width}" fill="{ring}"/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{PANEL_2}"/>'
    if image_uri:
        out += (f'<clipPath id="{uid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
                f'<image href="{image_uri}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
                f'clip-path="url(#{uid})" preserveAspectRatio="xMidYMid slice"/>')
    else:
        out += text(cx, cy + r * 0.36, _initial(name), r, 700, SOFT, "middle")
    return out


def server_icon(x: float, y: float, size: float, image_uri: str | None, name: str, ring: str, uid: str, ring_width: float = 6) -> str:
    """Square server icon with cut corners and a colored frame (the website's server pages)."""
    out = shape(x - ring_width, y - ring_width, size + 2 * ring_width, size + 2 * ring_width, ring, 1, CUT)
    out += shape(x, y, size, size, PANEL_2, 1, CUT - ring_width * 0.6)
    if image_uri:
        out += (f'<clipPath id="{uid}"><polygon points="{cut_points(x, y, size, size, CUT - ring_width * 0.6)}"/></clipPath>'
                f'<image href="{image_uri}" x="{x}" y="{y}" width="{size}" height="{size}" '
                f'clip-path="url(#{uid})" preserveAspectRatio="xMidYMid slice"/>')
    else:
        out += text(x + size / 2, y + size / 2 + size * 0.18, _initial(name), size / 2, 700, SOFT, "middle")
    return out


# ---------------------------------------------------------------------------
# Document and export
# ---------------------------------------------------------------------------
def document(w: int, h: int, body: str, accent: str = ACCENT, bg: str = BG, halo: str | None = None) -> str:
    """Full SVG card: cut-corner frame, the website's dark background with two soft halos, colored top edge.
    Displayed at half size: the canvas is 2x."""
    halo = halo or MEMBER
    frame = cut_points(0, 0, w, h, 32)
    defs = (f'<defs><clipPath id="frame"><polygon points="{frame}"/></clipPath>'
            f'<radialGradient id="halo1" cx="0.08" cy="0" r="0.75"><stop offset="0" stop-color="{accent}" stop-opacity="0.20"/>'
            f'<stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="halo2" cx="1" cy="1" r="0.6"><stop offset="0" stop-color="{halo}" stop-opacity="0.10"/>'
            f'<stop offset="1" stop-color="{halo}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="holo" x1="0" y1="0" x2="1" y2="0.3">'
            f'<stop offset="0" stop-color="#ff7bd5"/><stop offset="0.25" stop-color="#ffd36e"/><stop offset="0.5" stop-color="#5ff0b0"/>'
            f'<stop offset="0.75" stop-color="#6fb6ff"/><stop offset="1" stop-color="#b07cff"/></linearGradient></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w // 2}" height="{h // 2}" viewBox="0 0 {w} {h}">{defs}'
            f'<g clip-path="url(#frame)"><rect width="{w}" height="{h}" fill="{bg}"/>'
            f'<rect width="{w}" height="{h}" fill="url(#halo1)"/><rect width="{w}" height="{h}" fill="url(#halo2)"/>{body}</g>'
            f'<polygon points="{cut_points(1, 1, w - 2, h - 2, 31)}" fill="none" stroke="{LINE}" stroke-width="2"/>'
            f'<polyline points="1,33 33,1 {w * 0.42:.0f},1" fill="none" stroke="{accent}" stroke-width="4"/>'
            f'</svg>')


def to_png(svg: str) -> bytes:
    """Rasterize a card with resvg at full canvas size (the 2x image Discord displays sharply)."""
    import resvg_py
    data = resvg_py.svg_to_bytes(svg_string=svg, zoom=2, font_dirs=[FONT_DIR], skip_system_fonts=True,
                                 font_family="Chakra Petch", sans_serif_family="HG Sans")
    return bytes(data)
