"""Design system of the stat cards: website colors, Inter font, SVG primitives, images and PNG export.

Cards are meant to be read at small size (a Discord image is usually seen without clicking, around
500 px wide): they are drawn on a large canvas (1200 px wide) with big type, then shown at half size
as SVG or exported as a sharp 2x PNG. No text should be smaller than ~24 px on the canvas.
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

log = logging.getLogger(__name__)

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")
FONT_FAMILY = "Inter, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
_FONT_FILES = {400: "Inter-Regular.ttf", 600: "Inter-SemiBold.ttf", 700: "Inter-Bold.ttf", 800: "Inter-ExtraBold.ttf", 900: "Inter-Black.ttf"}

# Website palette (static/styles.css, pages/profile_theme.css)
BG = "#0b1220"
BG_2 = "#111a2b"
TEXT = "#f1f5f9"
SOFT = "#cbd5e1"
MUTED = "#94a3b8"
DIM = "#64748b"
LINE = "#ffffff"          # used with a low opacity for borders and panels
VOICE = "#38bdf8"
MESSAGES = "#818cf8"
GOLD = "#fbbf24"
SILVER = "#cbd5e1"
BRONZE = "#f59e0b"
WIN = "#34d399"
SITE = "hourglassbot.net"


# ---------------------------------------------------------------------------
# Text: measured with the same Inter files resvg draws with
# ---------------------------------------------------------------------------
@lru_cache(maxsize=64)
def _font(weight: int, size: int) -> ImageFont.FreeTypeFont:
    name = _FONT_FILES.get(weight) or _FONT_FILES[700]
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


@lru_cache(maxsize=1)
def _inter_codepoints() -> frozenset:
    """Characters Inter can draw (its cmap); every weight shares the same character set."""
    from fontTools.ttLib import TTFont
    with TTFont(os.path.join(FONT_DIR, _FONT_FILES[700]), lazy=True) as font:
        return frozenset(font.getBestCmap())


def clean(value) -> str:
    """Drop what Inter cannot draw (emoji, CJK...) instead of showing empty boxes; collapse the spaces left."""
    raw = str(value if value is not None else "")
    codepoints = _inter_codepoints()
    kept = "".join(ch for ch in raw if ch.isspace() or ord(ch) in codepoints)
    return " ".join(kept.split()) if kept != raw else raw


def text_width(text: str, size: float, weight: int = 700) -> float:
    """Width in canvas pixels (measured at 4x for sub-pixel precision)."""
    return _font(weight, max(1, round(size * 4))).getlength(clean(text)) / 4


def fit_text(text: str, max_width: float, size: float, weight: int = 700, min_size: float | None = None) -> tuple[str, float]:
    """Shrink the font down to min_size, then shorten with an ellipsis, so the text fits max_width."""
    text = clean(text)
    min_size = min_size or size
    while size > min_size and text_width(text, size, weight) > max_width:
        size -= 1
    if text_width(text, size, weight) <= max_width:
        return text, size
    while len(text) > 1 and text_width(text + "…", size, weight) > max_width:
        text = text[:-1]
    return text.rstrip() + "…", size


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def text(x: float, y: float, value: str, size: float, weight: int = 700, fill: str = TEXT,
         anchor: str = "start", opacity: float | None = None, spacing: float | None = None) -> str:
    extra = f' fill-opacity="{opacity}"' if opacity is not None else ""
    if spacing:
        extra += f' letter-spacing="{spacing}"'
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT_FAMILY}" font-size="{size:.1f}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{extra}>{esc(clean(value))}</text>')


def label(x: float, y: float, value: str, size: float = 24, fill: str = MUTED, anchor: str = "start") -> str:
    """Small uppercase caption above a value."""
    return text(x, y, value.upper(), size, 700, fill, anchor, spacing=1.5)


def rect(x: float, y: float, w: float, h: float, r: float, fill: str, opacity: float = 1,
         stroke: str | None = None, stroke_opacity: float = 0.1, stroke_width: float = 2) -> str:
    out = f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0, w):.1f}" height="{max(0, h):.1f}" rx="{r}" fill="{fill}"'
    if opacity != 1:
        out += f' fill-opacity="{opacity}"'
    if stroke:
        out += f' stroke="{stroke}" stroke-opacity="{stroke_opacity}" stroke-width="{stroke_width}"'
    return out + "/>"


def panel(x: float, y: float, w: float, h: float, r: float = 24, tint: str = LINE, opacity: float = 0.045) -> str:
    """Card surface of the website (gray-box): faint fill and hairline border."""
    return rect(x, y, w, h, r, tint, opacity, stroke=LINE, stroke_opacity=0.09)


def pill(x: float, y: float, value: str, color: str, size: float = 26, h: float = 48, anchor: str = "start",
         weight: int = 800, max_width: float | None = None) -> tuple[str, float]:
    """Rounded chip (tinted background, colored text). Returns (svg, width)."""
    pad = h * 0.45
    if max_width:
        value, size = fit_text(value, max_width - 2 * pad, size, weight, size * 0.8)
    w = text_width(value, size, weight) + 2 * pad
    left = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
    svg = (rect(left, y, w, h, h / 2, color, 0.14, stroke=color, stroke_opacity=0.45)
           + text(left + w / 2, y + h / 2 + size * 0.36, value, size, weight, color, "middle"))
    return svg, w


def progress(x: float, y: float, w: float, h: float, ratio: float, color: str, color_2: str | None = None, uid: str = "p") -> str:
    ratio = max(0.0, min(1.0, ratio))
    fill_w = max(h, w * ratio) if ratio > 0 else 0
    grad = ""
    paint = color
    if color_2:
        grad = (f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="1" y2="0">'
                f'<stop offset="0" stop-color="{color}"/><stop offset="1" stop-color="{color_2}"/></linearGradient></defs>')
        paint = f"url(#{uid})"
    return grad + rect(x, y, w, h, h / 2, LINE, 0.08) + (rect(x, y, fill_w, h, h / 2, paint) if fill_w else "")


def icon(inner_svg: str, x: float, y: float, size: float, color: str, stroke: float = 2) -> str:
    """Lucide-style 24x24 icon (badge svg_path) drawn at (x, y) with the given size."""
    s = size / 24
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.4f})" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{inner_svg}</g>')


ICONS = {
    "mic": '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "trophy": '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/><path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/><path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "headphones": '<path d="M3 14h3a2 2 0 0 1 2 2v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a9 9 0 0 1 18 0v7a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3"/>',
    "star": '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
    "hourglass": '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    "crown": '<path d="m2 4 3 12h14l3-12-6 7-4-7-4 7-6-7zm3 16h14"/>',
}


# ---------------------------------------------------------------------------
# Numbers and colors
# ---------------------------------------------------------------------------
def fmt_int(n) -> str:
    return f"{int(n or 0):,}"


def fmt_hours(seconds) -> str:
    """Voice time: 35m, 45.2h, 771h, 12,450h."""
    seconds = int(seconds or 0)
    if seconds < 3600:
        return f"{seconds // 60}m"
    hours = seconds / 3600
    return f"{hours:.1f}h" if hours < 100 else f"{int(hours):,}h"


def fmt_date(value) -> str:
    return value.strftime("%b %d, %Y").replace(" 0", " ") if value else "—"


def hex_rgb(hex_color: str) -> tuple[int, int, int]:
    h = (hex_color or "#38bdf8").lstrip("#")
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


def avatar(cx: float, cy: float, r: float, image_uri: str | None, name: str, ring: str, uid: str, ring_width: float = 7) -> str:
    """Round avatar with a colored ring; the initial on a dark disc when there is no picture."""
    out = f'<circle cx="{cx}" cy="{cy}" r="{r + ring_width}" fill="{ring}"/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#1e293b"/>'
    if image_uri:
        out += (f'<clipPath id="{uid}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
                f'<image href="{image_uri}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
                f'clip-path="url(#{uid})" preserveAspectRatio="xMidYMid slice"/>')
    else:
        initial = (name or "?").strip()[:1].upper() or "?"
        out += text(cx, cy + r * 0.36, initial, r, 900, SOFT, "middle")
    return out


# ---------------------------------------------------------------------------
# Document and export
# ---------------------------------------------------------------------------
def document(w: int, h: int, body: str, bg: str = BG, radius: int = 36, glow: str | None = None) -> str:
    """Full SVG card (rounded, transparent corners). Displayed at half size: the canvas is 2x."""
    glow_svg = ""
    if glow:
        glow_svg = (f'<defs><radialGradient id="glow" cx="0.15" cy="0" r="0.9">'
                    f'<stop offset="0" stop-color="{glow}" stop-opacity="0.22"/>'
                    f'<stop offset="1" stop-color="{glow}" stop-opacity="0"/></radialGradient></defs>'
                    f'<rect width="{w}" height="{h}" rx="{radius}" fill="url(#glow)"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w // 2}" height="{h // 2}" viewBox="0 0 {w} {h}">'
            f'<defs><clipPath id="frame"><rect width="{w}" height="{h}" rx="{radius}"/></clipPath>'
            f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{bg}"/>'
            f'<stop offset="1" stop-color="{BG_2 if bg == BG else bg}"/></linearGradient></defs>'
            f'<g clip-path="url(#frame)"><rect width="{w}" height="{h}" fill="url(#bg)"/>{glow_svg}{body}</g>'
            f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{radius - 1}" fill="none" stroke="{LINE}" stroke-opacity="0.1" stroke-width="2"/>'
            f'</svg>')


def to_png(svg: str) -> bytes:
    """Rasterize a card with resvg at full canvas size (the 2x image Discord displays sharply)."""
    import resvg_py
    data = resvg_py.svg_to_bytes(svg_string=svg, zoom=2, font_dirs=[FONT_DIR], skip_system_fonts=True,
                                 font_family="Inter", sans_serif_family="Inter")
    return bytes(data)
