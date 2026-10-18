"""Generate the profile image gallery: banners and page backgrounds, all original procedural art.

Each theme is drawn with numpy/Pillow (no third-party images, nothing to license). Banners are 1600x400,
backgrounds 1920x1080 (darker and softer so text stays readable), each with a small thumbnail for the picker.

Usage (from web/, requires Pillow and numpy):
    python scripts/make_profile_gallery.py app/static/images/profile [theme1,theme2]
"""

import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "app/static/images/profile")
BANNER = (1600, 400)
BACKGROUND = (1920, 1080)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def gradient(h: int, w: int, stops: list[tuple[float, str]], axis: int = 0) -> np.ndarray:
    """Linear gradient (vertical by default) through colour stops [(position 0..1, '#rrggbb')]."""
    n = h if axis == 0 else w
    t = np.linspace(0, 1, n, dtype=np.float32)
    pos = np.array([p for p, _ in stops], dtype=np.float32)
    cols = np.stack([hex_rgb(c) for _, c in stops])
    line = np.stack([np.interp(t, pos, cols[:, k]) for k in range(3)], axis=-1)
    if axis == 0:
        return np.repeat(line[:, None, :], w, axis=1)
    return np.repeat(line[None, :, :], h, axis=0)


def noise(h: int, w: int, rng: np.random.Generator, octaves: int = 5, base: int = 4, stretch=(1.0, 1.0)) -> np.ndarray:
    """Fractal value noise in 0..1 (random grids upscaled with bicubic filtering and summed)."""
    acc = np.zeros((h, w), dtype=np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        gh = max(2, int(base * (2 ** o) * stretch[0]))
        gw = max(2, int(base * (2 ** o) * stretch[1] * w / h))
        grid = rng.random((gh, gw)).astype(np.float32)
        layer = np.asarray(Image.fromarray(grid, mode="F").resize((w, h), Image.BICUBIC))
        acc += layer * amp
        total += amp
        amp *= 0.5
    acc /= total
    return np.clip((acc - acc.min()) / (acc.max() - acc.min() + 1e-6), 0, 1)


def blend(base: np.ndarray, color: str | np.ndarray, alpha: np.ndarray) -> np.ndarray:
    c = hex_rgb(color) if isinstance(color, str) else color
    a = np.clip(alpha, 0, 1)[..., None]
    return base * (1 - a) + c * a


def screen(base: np.ndarray, color: str, amount: np.ndarray) -> np.ndarray:
    c = hex_rgb(color) / 255.0
    a = np.clip(amount, 0, 1)[..., None]
    b = base / 255.0
    return (1 - (1 - b) * (1 - c * a)) * 255.0


def stars(img: np.ndarray, rng: np.random.Generator, count: int, max_y: float = 1.0, glow: bool = True) -> np.ndarray:
    h, w, _ = img.shape
    pil = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        x, y = rng.random() * w, rng.random() * h * max_y
        r = rng.choice([0.6, 0.8, 1.0, 1.3, 1.8], p=[0.35, 0.3, 0.2, 0.1, 0.05])
        v = int(140 + rng.random() * 115)
        d.ellipse((x - r, y - r, x + r, y + r), fill=v)
    if glow:
        halo = layer.filter(ImageFilter.GaussianBlur(2.5))
        layer = Image.fromarray(np.maximum(np.asarray(layer), np.asarray(halo).astype(np.float32) * 1.6).clip(0, 255).astype(np.uint8))
    a = np.asarray(layer).astype(np.float32) / 255.0
    return np.asarray(pil).astype(np.float32) * (1 - a[..., None]) + 255 * a[..., None]


def ridge(w: int, rng: np.random.Generator, base: float, amp: float, rough: int = 6) -> np.ndarray:
    """1D fractal profile (heights in pixels) for mountains, dunes, skylines."""
    xs = np.zeros(w, dtype=np.float32)
    a = amp
    for o in range(rough):
        n = 3 * 2 ** o
        pts = rng.random(n + 1) * 2 - 1
        xs += np.interp(np.linspace(0, n, w), np.arange(n + 1), pts) * a
        a *= 0.5
    return base + xs


def fill_below(img: np.ndarray, profile: np.ndarray, color: str | np.ndarray, top_shade: float = 0.0) -> np.ndarray:
    h, w, _ = img.shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    mask = yy >= profile[None, :]
    c = hex_rgb(color) if isinstance(color, str) else color
    out = img.copy()
    if top_shade:
        depth = np.clip((yy - profile[None, :]) / (h * 0.35), 0, 1)
        shade = (c * (1 - top_shade) + c * top_shade * 0.4)[None, None, :] * depth[..., None] + c * (1 - depth[..., None])
        out[mask] = shade[mask]
    else:
        out[mask] = c
    return out


def vignette(img: np.ndarray, strength: float = 0.35) -> np.ndarray:
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return img * (1 - strength * np.clip(d - 0.4, 0, 1))[..., None]


def to_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ------------------------------------------------------------------------------
# Themes: each returns an RGB float array of shape (h, w, 3)
# ------------------------------------------------------------------------------

def aurora(w, h, rng):
    img = gradient(h, w, [(0, "#020617"), (0.6, "#0b1f3a"), (1, "#0f2a3d")])
    img = stars(img, rng, int(w * h / 2500), max_y=0.8)
    x = np.linspace(0, 1, w, dtype=np.float32)
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    streaks = noise(h, w, rng, octaves=4, base=2, stretch=(0.15, 2.5))
    for k, (col, top) in enumerate([("#34d399", "#22d3ee"), ("#a78bfa", "#34d399"), ("#2dd4bf", "#818cf8")]):
        phase = rng.random() * 6.28
        center = 0.35 + 0.12 * k + 0.08 * np.sin(x * (3 + k) + phase) + 0.05 * np.sin(x * 11 + phase * 2)
        band = np.exp(-((yy - center[None, :]) / (0.09 + 0.03 * k)) ** 2)
        tail = np.clip((center[None, :] - yy) / 0.35, 0, 1) * (yy < center[None, :])
        curtain = (band * 0.9 + tail * 0.45 * band.max(axis=0, keepdims=True) * np.exp(-((center[None, :] - yy) / 0.25) ** 2)) * (0.45 + 0.75 * streaks)
        img = screen(img, col, curtain * 0.85)
        img = screen(img, top, curtain * np.clip(1 - yy * 2.2, 0, 1) * 0.5)
    img = fill_below(img, ridge(w, rng, h * 0.86, h * 0.07), "#020812")
    return vignette(img, 0.3)


def nebula(w, h, rng):
    img = gradient(h, w, [(0, "#05030f"), (1, "#0b0620")])
    n1 = noise(h, w, rng, octaves=6, base=3)
    n2 = noise(h, w, rng, octaves=6, base=3)
    n3 = noise(h, w, rng, octaves=5, base=2)
    img = screen(img, "#7c3aed", np.clip((n1 - 0.35) * 1.8, 0, 1) * 0.9)
    img = screen(img, "#ec4899", np.clip((n2 - 0.5) * 2.2, 0, 1) * 0.8)
    img = screen(img, "#38bdf8", np.clip((n3 - 0.6) * 2.5, 0, 1) * 0.55)
    dust = noise(h, w, rng, octaves=6, base=6)
    img = img * (0.75 + 0.35 * dust[..., None])
    img = stars(img, rng, int(w * h / 1200))
    return vignette(img, 0.4)


def synthwave(w, h, rng):
    horizon = int(h * 0.62)
    img = gradient(h, w, [(0, "#0b0221"), (0.35, "#3b0764"), (0.62, "#db2777"), (0.621, "#1a0533"), (1, "#0b0221")])
    img = stars(img, rng, int(w * h / 4000), max_y=0.4)
    # Striped sun
    sun = Image.new("L", (w, h), 0)
    cx, cy, r = w * 0.5, horizon - h * 0.02, h * 0.42
    ImageDraw.Draw(sun).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    s = np.asarray(sun).astype(np.float32) / 255.0
    yy = np.arange(h, dtype=np.float32)[:, None]
    stripes = np.ones_like(s)
    for i in range(7):
        y0 = cy - r * 0.62 + i * r * 0.09
        gap = 1 + i * 1.6
        stripes[(yy[:, 0] > y0) & (yy[:, 0] < y0 + gap), :] = 0
    s = s * stripes * (yy < horizon)
    sun_col = gradient(h, w, [(0, "#fde047"), (0.45, "#fb923c"), (0.62, "#f43f5e"), (1, "#f43f5e")])
    glow = np.asarray(sun.filter(ImageFilter.GaussianBlur(h * 0.12))).astype(np.float32) / 255.0
    img = screen(img, "#f472b6", glow * 0.6 * (yy < horizon))
    img = img * (1 - s[..., None]) + sun_col * s[..., None]
    # Mountains behind the grid
    img = fill_below(img, np.minimum(ridge(w, rng, horizon - h * 0.04, h * 0.06), horizon), "#1e0a3c")
    # Perspective grid
    grid = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(grid)
    for i in range(1, 16):
        t = (i / 15) ** 2.2
        y = horizon + t * (h - horizon)
        d.line((0, y, w, y), fill=255, width=2)
    for i in range(-24, 25):
        d.line((w / 2 + i * w * 0.012, horizon, w / 2 + i * w * 0.11, h), fill=255, width=2)
    g = np.asarray(grid).astype(np.float32) / 255.0 * (yy >= horizon)
    gblur = np.asarray(grid.filter(ImageFilter.GaussianBlur(4))).astype(np.float32) / 255.0 * (yy >= horizon)
    fade = np.clip((yy - horizon) / (h - horizon), 0.25, 1)
    img = screen(img, "#e879f9", np.clip(g * 0.9 + gblur * 1.2, 0, 1) * fade)
    return img


def mountains(w, h, rng):
    img = gradient(h, w, [(0, "#0f172a"), (0.45, "#4c1d95"), (0.75, "#f97316"), (1, "#fbbf24")])
    img = stars(img, rng, int(w * h / 6000), max_y=0.35, glow=False)
    sun = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sun).ellipse((w * 0.7, h * 0.16, w * 0.7 + h * 0.24, h * 0.40), fill=255)
    img = screen(img, "#fde68a", np.asarray(sun.filter(ImageFilter.GaussianBlur(30))).astype(np.float32) / 255.0 * 0.8)
    img = screen(img, "#fff7ed", np.asarray(sun).astype(np.float32) / 255.0 * 0.9)
    layers = [("#5b2a6e", 0.50, 0.16), ("#3b1d5c", 0.62, 0.13), ("#24123f", 0.74, 0.10), ("#120a24", 0.86, 0.08)]
    for col, base, amp in layers:
        img = fill_below(img, ridge(w, rng, h * base, h * amp, rough=7), col)
        # atmospheric haze between layers
        yy = np.arange(h, dtype=np.float32)[:, None] / h
        img = screen(img, "#fb923c", np.exp(-((yy - base - 0.06) / 0.05) ** 2) * np.ones((1, w)) * 0.12)
    return img


def ocean(w, h, rng):
    img = gradient(h, w, [(0, "#020617"), (0.45, "#0c2a4d"), (0.5, "#0e3a5f"), (1, "#020617")])
    img = stars(img, rng, int(w * h / 3500), max_y=0.4)
    moon = Image.new("L", (w, h), 0)
    ImageDraw.Draw(moon).ellipse((w * 0.2, h * 0.12, w * 0.2 + h * 0.18, h * 0.30), fill=255)
    m = np.asarray(moon).astype(np.float32) / 255.0
    img = screen(img, "#bae6fd", np.asarray(moon.filter(ImageFilter.GaussianBlur(25))).astype(np.float32) / 255.0 * 0.6)
    img = blend(img, "#e0f2fe", m)
    x = np.arange(w, dtype=np.float32)
    cols = ["#0c4a6e", "#075985", "#0369a1", "#0e7490", "#155e75", "#083344"]
    for i, col in enumerate(cols):
        base = h * (0.5 + i * 0.09)
        prof = base + np.sin(x / (60 + i * 25) + rng.random() * 6) * (6 + i * 4) + np.sin(x / (23 + i * 7) + rng.random() * 6) * (3 + i)
        img = fill_below(img, prof, col)
        crest = np.zeros((h, w), dtype=np.float32)
        yy = np.arange(h, dtype=np.float32)[:, None]
        crest = np.exp(-((yy - prof[None, :]) / 2.2) ** 2)
        img = screen(img, "#7dd3fc", crest * 0.35)
    # moon reflection
    yy = np.arange(h, dtype=np.float32)[:, None] / h
    xx = np.arange(w, dtype=np.float32)[None, :] / w
    refl = np.exp(-((xx - 0.2 - h * 0.09 / w) / 0.03) ** 2) * (yy > 0.5) * noise(h, w, rng, octaves=3, base=2, stretch=(4, 0.3))
    img = screen(img, "#e0f2fe", refl * 0.5)
    return img


def lowpoly(w, h, rng):
    cell = h / 4
    cols, rows = int(w / cell) + 2, 6
    pts = np.zeros((rows, cols, 2), dtype=np.float32)
    for r in range(rows):
        for c in range(cols):
            jx = (rng.random() - 0.5) * cell * 0.8 if 0 < c < cols - 1 else 0
            jy = (rng.random() - 0.5) * cell * 0.8 if 0 < r < rows - 1 else 0
            pts[r, c] = (c * cell + jx - cell * 0.5, r * h / (rows - 1) + jy)
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    c1, c2, c3 = hex_rgb("#1e1b4b"), hex_rgb("#4338ca"), hex_rgb("#06b6d4")
    for r in range(rows - 1):
        for c in range(cols - 1):
            a, b, cc, dd = pts[r, c], pts[r, c + 1], pts[r + 1, c], pts[r + 1, c + 1]
            for tri in ((a, b, cc), (b, dd, cc)):
                cx = sum(p[0] for p in tri) / 3 / w
                cy = sum(p[1] for p in tri) / 3 / h
                t = np.clip(cx * 0.8 + (1 - cy) * 0.3 + (rng.random() - 0.5) * 0.18, 0, 1)
                col = c1 * (1 - t) * (1 - t) + c2 * 2 * t * (1 - t) + c3 * t * t
                col = col * (0.85 + rng.random() * 0.25)
                d.polygon([tuple(p) for p in tri], fill=tuple(int(v) for v in np.clip(col, 0, 255)))
    return vignette(np.asarray(im).astype(np.float32), 0.35)


def topo(w, h, rng):
    img = gradient(h, w, [(0, "#04141a"), (1, "#062a2f")], axis=1)
    field = noise(h, w, rng, octaves=4, base=2)
    levels = field * 18
    frac = np.abs(levels - np.round(levels))
    lines = np.clip(1 - frac / 0.06, 0, 1)
    major = (np.round(levels) % 5 == 0) * lines
    img = screen(img, "#2dd4bf", lines * 0.45 + major * 0.4)
    img = screen(img, "#0ea5e9", np.clip((field - 0.6) * 2, 0, 1) * 0.25)
    return vignette(img, 0.35)


def pixel_city(w, h, rng):
    """Pixel-art night skyline drawn at 1/8 scale then enlarged with nearest-neighbour (the site's pixel DA)."""
    s = 8
    pw, ph = w // s, h // s
    sky = gradient(ph, pw, [(0, "#0b1026"), (0.55, "#1e1b4b"), (0.8, "#5b21b6"), (1, "#7c3aed")])
    sky = np.round(sky / 18) * 18  # colour banding, retro look
    img = sky.copy()
    for _ in range(int(pw * ph / 110)):
        x, y = rng.integers(0, pw), rng.integers(0, int(ph * 0.55))
        img[y, x] = hex_rgb("#e2e8f0") if rng.random() > 0.3 else hex_rgb("#a5b4fc")
    # moon
    mx, my = int(pw * 0.82), int(ph * 0.22)
    for yy in range(-4, 5):
        for xx in range(-4, 5):
            if xx * xx + yy * yy <= 16 and (xx + 2) ** 2 + (yy - 1) ** 2 > 9:
                img[my + yy, mx + xx] = hex_rgb("#fde68a")
    tall = 0.5 if h / w > 0.4 else 1.0
    for layer, (col, win, hmin, hmax) in enumerate([("#1e1b4b", "#6366f1", 0.35 * tall, 0.65 * tall), ("#0f0a2a", "#fbbf24", 0.45 * tall, 0.8 * tall)]):
        x = 0
        while x < pw:
            bw = min(int(rng.integers(4, 10)), pw - x)
            bh = int(ph * (hmin + rng.random() * (hmax - hmin)))
            top = ph - bh
            img[top:, x:x + bw] = hex_rgb(col)
            if rng.random() > 0.6:
                img[top - 2:top, x + bw // 2:x + bw // 2 + 1] = hex_rgb(col)
            for wy in range(top + 2, ph - 1, 3):
                for wx in range(x + 1, x + bw - 1, 2):
                    if rng.random() > 0.55:
                        img[wy, wx] = hex_rgb(win) * (0.7 + 0.3 * rng.random())
            x += bw + int(rng.integers(0, 2))
    return np.asarray(to_image(img).resize((w, h), Image.NEAREST)).astype(np.float32)


def sakura(w, h, rng):
    img = gradient(h, w, [(0, "#1a0b1e"), (1, "#3b0f2e")], axis=1)
    img = screen(img, "#f472b6", noise(h, w, rng, octaves=4, base=2) * 0.25)
    bokeh = Image.new("RGB", (w, h), (0, 0, 0))
    d = ImageDraw.Draw(bokeh)
    for _ in range(70):
        r = rng.random() * h * 0.12 + 8
        x, y = rng.random() * w, rng.random() * h
        col = [(244, 114, 182), (251, 207, 232), (192, 132, 252), (253, 164, 175)][rng.integers(0, 4)]
        k = 0.25 + rng.random() * 0.5
        d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * k) for c in col))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(6))
    img = 255 - (255 - img) * (255 - np.asarray(bokeh).astype(np.float32)) / 255
    petals = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(petals)
    for _ in range(90):
        x, y, s = rng.random() * w, rng.random() * h, rng.random() * 7 + 4
        pet = Image.new("RGBA", (int(s * 4), int(s * 4)), (0, 0, 0, 0))
        ImageDraw.Draw(pet).ellipse((s, s * 1.4, s * 3, s * 2.6), fill=(252, 231, 243, int(150 + rng.random() * 100)))
        pet = pet.rotate(rng.random() * 360, resample=Image.BICUBIC)
        petals.alpha_composite(pet, (int(x), int(y)))
    base = to_image(img).convert("RGBA")
    base.alpha_composite(petals)
    return np.asarray(base.convert("RGB")).astype(np.float32)


def ember(w, h, rng):
    img = gradient(h, w, [(0, "#0c0505"), (0.6, "#2a0a06"), (1, "#7c2d12")])
    heat = noise(h, w, rng, octaves=5, base=3, stretch=(0.5, 1.5))
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = screen(img, "#f97316", heat * yy ** 2 * 0.9)
    img = screen(img, "#fde047", np.clip(heat - 0.55, 0, 1) * yy ** 3 * 1.5)
    sparks = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(sparks)
    for _ in range(int(w * h / 3000)):
        x = rng.random() * w
        y = h * (1 - rng.random() ** 1.8)
        r = rng.random() * 2.2 + 0.6
        d.ellipse((x - r, y - r, x + r, y + r), fill=int(120 + rng.random() * 135))
    sp = np.asarray(sparks).astype(np.float32) / 255.0
    glow = np.asarray(sparks.filter(ImageFilter.GaussianBlur(4))).astype(np.float32) / 255.0
    img = screen(img, "#fdba74", np.clip(sp + glow * 2, 0, 1))
    return vignette(img, 0.35)


def circuit(w, h, rng):
    img = gradient(h, w, [(0, "#020617"), (1, "#0b1530")], axis=1)
    lines = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(lines)
    step = 20
    for _ in range(int(w / 12)):
        x, y = rng.integers(0, w // step) * step, rng.integers(0, h // step) * step
        pts = [(x, y)]
        dx, dy = [(1, 0), (0, 1), (-1, 0), (0, -1)][rng.integers(0, 4)]
        for _ in range(rng.integers(3, 9)):
            n = rng.integers(2, 8) * step
            x, y = x + dx * n, y + dy * n
            pts.append((x, y))
            if rng.random() > 0.5:  # 45 degree turn
                ex, ey = (dx + dy, dy - dx) if rng.random() > 0.5 else (dx - dy, dy + dx)
                x, y = x + ex * step, y + ey * step
                pts.append((x, y))
            dx, dy = (dy, -dx) if rng.random() > 0.5 else (-dy, dx)
        d.line(pts, fill=200, width=2, joint="curve")
        for px, py in (pts[0], pts[-1]):
            d.ellipse((px - 5, py - 5, px + 5, py + 5), outline=255, width=2)
    l = np.asarray(lines).astype(np.float32) / 255.0
    glow = np.asarray(lines.filter(ImageFilter.GaussianBlur(5))).astype(np.float32) / 255.0
    tint = gradient(h, w, [(0, "#22d3ee"), (1, "#818cf8")], axis=1)
    a = np.clip(l * 0.75 + glow * 1.4, 0, 1)[..., None]
    img = img * (1 - a) + tint * a
    return vignette(img, 0.4)


def dunes(w, h, rng):
    img = gradient(h, w, [(0, "#0b1026"), (0.5, "#312e81"), (0.7, "#9a3412"), (1, "#451a03")])
    img = stars(img, rng, int(w * h / 3000), max_y=0.45)
    moon = Image.new("L", (w, h), 0)
    ImageDraw.Draw(moon).ellipse((w * 0.75, h * 0.1, w * 0.75 + h * 0.16, h * 0.26), fill=255)
    img = screen(img, "#fde68a", np.asarray(moon.filter(ImageFilter.GaussianBlur(25))).astype(np.float32) / 255.0 * 0.5)
    img = blend(img, "#fef3c7", np.asarray(moon).astype(np.float32) / 255.0)
    x = np.arange(w, dtype=np.float32)
    yy = np.arange(h, dtype=np.float32)[:, None]
    for i, (lit, dark) in enumerate([("#b45309", "#78350f"), ("#d97706", "#92400e"), ("#f59e0b", "#a16207"), ("#c2410c", "#7c2d12")]):
        base = h * (0.55 + i * 0.11)
        phase = rng.random() * 6.28
        prof = base + np.sin(x / (180 - i * 25) + phase) * h * 0.05 + np.sin(x / 57 + phase) * h * 0.012
        slope = np.gradient(prof)
        shade = np.clip(0.5 + slope * 0.9, 0, 1)
        col = hex_rgb(lit)[None, :] * shade[:, None] + hex_rgb(dark)[None, :] * (1 - shade[:, None])
        mask = yy >= prof[None, :]
        depth = np.clip((yy - prof[None, :]) / (h * 0.25), 0, 1)[..., None]
        layer = np.repeat(col[None, :, :], h, axis=0) * (1 - depth * 0.45)
        img = np.where(mask[..., None], layer, img)
    return vignette(img, 0.3)


# --- Background-only themes (calm, wide compositions made for the 16:9 page background) ---

def starfield(w, h, rng):
    img = gradient(h, w, [(0, "#02030a"), (1, "#070b1c")])
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    # diagonal milky way band
    d = (yy / h - 0.85 + xx / w * 0.7)
    band = np.exp(-(d / 0.16) ** 2) * (0.35 + 0.65 * noise(h, w, rng, octaves=6, base=4))
    img = screen(img, "#6366f1", band * 0.45)
    img = screen(img, "#f0abfc", np.clip(band - 0.55, 0, 1) * 0.6)
    img = stars(img, rng, int(w * h / 700))
    img = stars(img, rng, int(w * h / 9000) + int(band.sum() / 400), glow=True)
    return vignette(img, 0.35)


def hexgrid(w, h, rng):
    img = gradient(h, w, [(0, "#050816"), (1, "#0b1226")], axis=1)
    size = 34
    lines = Image.new("L", (w, h), 0)
    fills = Image.new("L", (w, h), 0)
    dl, df = ImageDraw.Draw(lines), ImageDraw.Draw(fills)
    hx = size * math.sqrt(3)
    for row in range(int(h / (size * 1.5)) + 2):
        for col in range(int(w / hx) + 2):
            cx = col * hx + (hx / 2 if row % 2 else 0)
            cy = row * size * 1.5
            pts = [(cx + size * math.cos(math.radians(60 * k + 30)), cy + size * math.sin(math.radians(60 * k + 30))) for k in range(6)]
            dl.polygon(pts, outline=200, width=2)
            if rng.random() > 0.93:
                df.polygon(pts, fill=int(90 + rng.random() * 120))
    l = np.asarray(lines).astype(np.float32) / 255.0
    f = np.asarray(fills.filter(ImageFilter.GaussianBlur(2))).astype(np.float32) / 255.0
    glow = np.asarray(fills.filter(ImageFilter.GaussianBlur(18))).astype(np.float32) / 255.0
    tint = gradient(h, w, [(0, "#22d3ee"), (1, "#a855f7")], axis=1)
    a = np.clip(l * 0.7 + f * 0.7 + glow * 0.8, 0, 1)[..., None]
    img = img * (1 - a) + tint * a
    return vignette(img, 0.45)


def forest(w, h, rng):
    img = gradient(h, w, [(0, "#06122b"), (0.5, "#1d4a6b"), (0.75, "#3b6f96"), (1, "#0b1a2a")])
    img = stars(img, rng, int(w * h / 2500), max_y=0.55)
    moon = Image.new("L", (w, h), 0)
    ImageDraw.Draw(moon).ellipse((w * 0.7, h * 0.12, w * 0.7 + h * 0.13, h * 0.25), fill=255)
    img = screen(img, "#e0f2fe", np.asarray(moon.filter(ImageFilter.GaussianBlur(40))).astype(np.float32) / 255.0 * 0.45)
    img = blend(img, "#f1f5f9", np.asarray(moon).astype(np.float32) / 255.0)
    yy = np.arange(h, dtype=np.float32)[:, None] / h
    for i, (col, base, tree_h) in enumerate([("#24506e", 0.66, 0.16), ("#143650", 0.74, 0.2), ("#081c2b", 0.84, 0.26)]):
        layer = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(layer)
        x = -20.0
        while x < w + 20:
            th = h * tree_h * (0.6 + rng.random() * 0.6)
            tw = th * 0.32
            ground = h * base + rng.random() * h * 0.03
            for k in range(4):  # stacked tiers of a pine
                top = ground - th + k * th * 0.18
                d.polygon([(x, top), (x - tw * (0.45 + k * 0.18), top + th * 0.38), (x + tw * (0.45 + k * 0.18), top + th * 0.38)], fill=255)
            d.rectangle((x - tw * 0.06, ground - th * 0.1, x + tw * 0.06, h), fill=255)
            x += tw * (0.55 + rng.random() * 0.7)
        d.rectangle((0, h * base + h * 0.02, w, h), fill=255)
        m = np.asarray(layer).astype(np.float32) / 255.0
        img = blend(img, col, m)
        img = screen(img, "#7dd3fc", np.exp(-((yy - base - 0.02) / 0.05) ** 2) * np.ones((1, w)) * 0.18)  # mist
    return vignette(img, 0.35)


def bokeh(w, h, rng):
    img = gradient(h, w, [(0, "#020617"), (1, "#0c1a3a")], axis=1)
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    for blur, count, rmax in ((14, 40, 0.16), (6, 60, 0.08), (2, 50, 0.035)):
        sub = Image.new("RGB", (w, h), (0, 0, 0))
        d = ImageDraw.Draw(sub)
        for _ in range(count):
            r = rng.random() * h * rmax + 6
            x, y = rng.random() * w, rng.random() * h
            col = [(56, 189, 248), (129, 140, 248), (45, 212, 191), (192, 132, 252)][rng.integers(0, 4)]
            k = 0.15 + rng.random() * 0.45
            d.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(c * k) for c in col))
        sub = sub.filter(ImageFilter.GaussianBlur(blur))
        layer = Image.fromarray(np.maximum(np.asarray(layer), np.asarray(sub)))
    img = 255 - (255 - img) * (255 - np.asarray(layer).astype(np.float32)) / 255
    return vignette(img, 0.4)


def flow(w, h, rng):
    img = gradient(h, w, [(0, "#05030f"), (1, "#0d0a24")])
    lines = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(lines)
    xs = np.linspace(-20, w + 20, 240)
    p1, p2 = rng.random() * 6, rng.random() * 6
    for i in range(46):
        t = i / 45
        ys = h * (0.25 + t * 0.55) + np.sin(xs / w * 5 + p1 + t * 2.2) * h * 0.12 + np.sin(xs / w * 11 + p2 - t * 3) * h * 0.035
        d.line(list(zip(xs, ys)), fill=int(110 + 145 * (1 - abs(t - 0.5) * 2)), width=3)
    l = np.asarray(lines).astype(np.float32) / 255.0
    glow = np.asarray(lines.filter(ImageFilter.GaussianBlur(10))).astype(np.float32) / 255.0
    tint = gradient(h, w, [(0, "#ec4899"), (0.5, "#8b5cf6"), (1, "#06b6d4")], axis=1)
    a = np.clip(l * 1.0 + glow * 1.6, 0, 1)[..., None]
    return vignette(img * (1 - a) + tint * a, 0.3)


def dotgrid(w, h, rng):
    img = gradient(h, w, [(0, "#060a14"), (1, "#0a1020")])
    dots = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(dots)
    step = 28
    for y in range(step // 2, h, step):
        for x in range(step // 2, w, step):
            d.ellipse((x - 2.4, y - 2.4, x + 2.4, y + 2.4), fill=255)
    dt = np.asarray(dots).astype(np.float32) / 255.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    glow = np.zeros((h, w), dtype=np.float32)
    tint = np.zeros((h, w, 3), dtype=np.float32)
    for cx, cy, col in ((0.2, 0.25, "#38bdf8"), (0.8, 0.7, "#a855f7"), (0.55, 0.15, "#2dd4bf")):
        g = np.exp(-(((xx / w - cx) * w / h) ** 2 + (yy / h - cy) ** 2) / 0.16)
        glow += g
        tint += g[..., None] * hex_rgb(col)
    tint = tint / np.maximum(glow[..., None], 1e-3)
    img = screen(img, "#334155", dt * 0.8)
    a = np.clip(dt * glow * 2.2, 0, 1)[..., None]
    img = img * (1 - a) + tint * a
    img = img + tint * np.clip(glow, 0, 1)[..., None] * 0.18
    return vignette(img, 0.3)


# --- Pop culture moods (anime / video games): original art only, no existing character, logo or scene ---

def _glow_layer(w, h):
    return Image.new("RGB", (w, h), (0, 0, 0))


def _add_glow(img, layer: Image.Image, radius: float, strength: float = 1.0, sharp: float = 1.0):
    """Screen a sharp + blurred copy of an RGB light layer onto the image (neon effect)."""
    sharp_a = np.asarray(layer).astype(np.float32) / 255.0
    soft_a = np.asarray(layer.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255.0
    light = np.clip(sharp_a * sharp + soft_a * 1.6 * strength, 0, 1)
    return 255 - (255 - img) * (1 - light)


def neon_city(w, h, rng):
    """Cyberpunk night: neon signs, lit windows, rain."""
    img = gradient(h, w, [(0, "#07010f"), (0.5, "#1f0638"), (0.78, "#6b1460"), (1, "#0d0318")])
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = screen(img, "#ff2e97", np.exp(-((yy - 0.78) / 0.08) ** 2) * np.ones((1, w)) * 0.35)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    neon = [(255, 46, 151), (0, 229, 255), (255, 214, 10), (154, 92, 255)]
    for layer, (col, hmin, hmax, win_p) in enumerate([((26, 10, 48), 0.35, 0.6, 0.12), ((17, 6, 33), 0.45, 0.78, 0.18), ((8, 3, 16), 0.55, 0.95, 0.22)]):
        x = -10.0
        while x < w:
            bw = h * (0.12 + rng.random() * 0.22)
            top = h * (1 - (hmin + rng.random() * (hmax - hmin)))
            d.rectangle((x, top, x + bw, h), fill=col)
            ws = max(3, h * 0.012)
            for wy in np.arange(top + ws * 2, h - ws, ws * 2.6):
                for wx in np.arange(x + ws, x + bw - ws, ws * 2.2):
                    if rng.random() < win_p:
                        c = neon[rng.integers(0, 4)] if rng.random() < 0.3 else (255, 196, 120)
                        k = 0.35 + 0.4 * rng.random() if layer < 2 else 0.8
                        d.rectangle((wx, wy, wx + ws, wy + ws * 0.8), fill=tuple(int(v * k) for v in c))
            if layer == 2 and rng.random() < 0.55:  # vertical neon sign
                sx = x + bw * (0.15 + rng.random() * 0.6)
                sy = top + h * 0.05 + rng.random() * h * 0.15
                c = neon[rng.integers(0, 4)]
                g.rectangle((sx, sy, sx + h * 0.022, sy + h * (0.12 + rng.random() * 0.12)), outline=c, width=max(2, int(h * 0.005)))
                for k in range(3):
                    yk = sy + h * 0.025 + k * h * 0.035
                    g.rectangle((sx + h * 0.006, yk, sx + h * 0.016, yk + h * 0.014), fill=c)
            if layer == 1 and rng.random() < 0.35:  # rooftop sign
                c = neon[rng.integers(0, 4)]
                g.rectangle((x + bw * 0.2, top - h * 0.04, x + bw * 0.8, top - h * 0.01), outline=c, width=max(2, int(h * 0.004)))
            x += bw + h * rng.random() * 0.02
    img = np.asarray(base).astype(np.float32)
    img = _add_glow(img, glow, radius=h * 0.02, strength=0.8)
    # rain
    rain = Image.new("L", (w, h), 0)
    r = ImageDraw.Draw(rain)
    for _ in range(int(w * h / 1800)):
        x0, y0, ln = rng.random() * w, rng.random() * h, h * (0.02 + rng.random() * 0.04)
        r.line((x0, y0, x0 - ln * 0.25, y0 + ln), fill=int(60 + rng.random() * 90), width=1)
    img = screen(img, "#9fd8ff", np.asarray(rain).astype(np.float32) / 255.0 * 0.6)
    return vignette(img, 0.35)


def pixel_dungeon(w, h, rng):
    """Retro RPG dungeon wall lit by torches (pixel art at 1/8 scale)."""
    s = 8
    pw, ph = w // s, h // s
    img = np.zeros((ph, pw, 3), dtype=np.float32)
    floor_y = int(ph * 0.78)
    tone = noise(ph, pw, rng, octaves=3, base=3)
    for y in range(floor_y):
        row, offset = y // 4, (y // 4) % 2 * 4
        for x in range(pw):
            mortar = (y % 4 == 3) or ((x + offset) % 8 == 7)
            if mortar:
                img[y, x] = hex_rgb("#1b1d2b")
            else:
                k = 0.75 + 0.35 * tone[y, x] + ((x + offset) // 8 * 7 + row * 3) % 5 * 0.03
                img[y, x] = hex_rgb("#4a5068") * k
    for y in range(floor_y, ph):
        for x in range(pw):
            edge = (y - floor_y) % 5 == 0 or (x + (y - floor_y) // 5 * 3) % 11 == 0
            img[y, x] = hex_rgb("#2a2433") if edge else hex_rgb("#3d3447") * (0.8 + 0.3 * tone[min(y, ph - 1), x])
    img[floor_y - 1:floor_y + 1, :] = hex_rgb("#141420")
    # torches and their light
    light = np.full((ph, pw), 0.18, dtype=np.float32)
    yy, xx = np.mgrid[0:ph, 0:pw].astype(np.float32)
    n_torch = max(2, pw // 45)
    for i in range(n_torch):
        tx = int((i + 0.5) * pw / n_torch + (rng.random() - 0.5) * 6)
        ty = int(ph * 0.42)
        light += np.exp(-((xx - tx) ** 2 + ((yy - ty) * 1.2) ** 2) / (2 * (ph * 0.35) ** 2)) * 1.1
        img[ty:ty + 5, tx:tx + 2] = hex_rgb("#5b3a1e")
        img[ty - 1, tx - 1:tx + 3] = hex_rgb("#3b2614")
        for fy, row in enumerate(["  y  ", " yoy ", "yoroy", " ror "]):
            for fx, ch in enumerate(row):
                if ch != " ":
                    img[ty - 5 + fy, tx - 2 + fx] = hex_rgb({"y": "#ffd23f", "o": "#ff8c1a", "r": "#e8451e"}[ch])
    warm = np.stack([light * 1.15, light * 0.85, light * 0.6], axis=-1)
    flame = (img[..., 0] > 200)[..., None]
    img = np.where(flame, img, img * np.clip(warm, 0, 1.4))
    img = np.round(img / 12) * 12  # limited palette
    out = np.asarray(to_image(img).resize((w, h), Image.NEAREST)).astype(np.float32)
    return vignette(out, 0.45)


def _invader(rng, size=(5, 7)):
    """Random symmetrical 8-bit sprite (generated, not copied from any game)."""
    half_w = (size[1] + 1) // 2
    grid = rng.random((size[0], half_w)) > 0.45
    grid[:, -1] |= rng.random(size[0]) > 0.3
    return np.concatenate([grid, grid[:, -2::-1] if size[1] % 2 else grid[:, ::-1]], axis=1)


def arcade(w, h, rng):
    """8-bit space shooter: rows of generated invaders, player ship, lasers, CRT glow."""
    s = 6
    pw, ph = w // s, h // s
    img = np.zeros((ph, pw, 3), dtype=np.float32) + hex_rgb("#03030a")
    for _ in range(pw * ph // 60):
        img[rng.integers(0, ph), rng.integers(0, pw)] = hex_rgb("#5d6b8a") * (0.5 + rng.random())
    colors = ["#ff4d6d", "#ffd23f", "#3ddc97", "#4cc9f0", "#c77dff"]
    rows = 3 if ph < 100 else 4
    sprite_w = 9
    for r in range(rows):
        sprite = _invader(rng, (5, 7))
        col = hex_rgb(colors[r % len(colors)])
        y0 = int(ph * 0.12) + r * 8
        step = sprite_w + 3
        x0 = (pw % step) // 2 + int(pw * 0.08)
        for x in range(x0, int(pw * 0.92) - sprite_w, step):
            for sy in range(5):
                for sx in range(7):
                    if sprite[sy, sx]:
                        img[y0 + sy, x + sx] = col
    # player ship and lasers
    sx, sy = pw // 2, ph - 8
    ship = ["   g   ", "  ggg  ", " ggggg ", "ggggggg", "gg g gg"]
    for yy_, row in enumerate(ship):
        for xx_, ch in enumerate(row):
            if ch == "g":
                img[sy + yy_ - 2, sx + xx_ - 3] = hex_rgb("#3ddc97")
    for lx in (sx, sx - int(pw * 0.25), sx + int(pw * 0.18)):
        ly = int(ph * (0.45 + rng.random() * 0.2))
        img[ly:ly + 4, lx] = hex_rgb("#f1faee")
    img = np.asarray(to_image(img).resize((w, h), Image.NEAREST)).astype(np.float32)
    glow = to_image(img).filter(ImageFilter.GaussianBlur(h * 0.012))
    img = 255 - (255 - img) * (255 - np.asarray(glow).astype(np.float32) * 0.7) / 255
    scan = (np.arange(h) % 3 == 0).astype(np.float32)[:, None, None]
    return vignette(img * (1 - scan * 0.22), 0.5)


def great_wave(w, h, rng):
    """Japanese woodblock print mood: layered waves with foam curls, red sun, paper texture."""
    paper = gradient(h, w, [(0, "#efe2c4"), (1, "#e2cfa6")])
    paper = paper * (0.93 + 0.07 * noise(h, w, rng, octaves=6, base=20)[..., None])
    base = to_image(paper)
    d = ImageDraw.Draw(base)
    r = h * 0.11
    d.ellipse((w * 0.78 - r, h * 0.22 - r, w * 0.78 + r, h * 0.22 + r), fill=(196, 48, 43))
    # distant mountain with snow cap
    mx = w * 0.62
    d.polygon([(mx - h * 0.35, h * 0.62), (mx, h * 0.36), (mx + h * 0.35, h * 0.62)], fill=(58, 82, 120))
    d.polygon([(mx - h * 0.09, h * 0.43), (mx, h * 0.36), (mx + h * 0.09, h * 0.43), (mx + h * 0.03, h * 0.41), (mx - h * 0.02, h * 0.44)], fill=(239, 226, 196))
    xs = np.linspace(0, w, 400)
    layers = [((25, 49, 89), 0.5, 0.05), ((44, 82, 128), 0.6, 0.06), ((23, 43, 79), 0.72, 0.07), ((52, 98, 148), 0.85, 0.05)]
    for col, base_y, amp in layers:
        ph_ = rng.random() * 6.28
        k = 2 + rng.random() * 3
        ys = h * base_y - np.abs(np.sin(xs / w * k * math.pi + ph_)) ** 3 * h * amp * 2.2
        d.polygon([(0, h)] + list(zip(xs, ys)) + [(w, h)], fill=col)
        d.line(list(zip(xs, ys)), fill=(245, 240, 228), width=max(2, int(h * 0.008)))
        # foam claws on crests
        for i in range(1, len(xs) - 1):
            if ys[i] < ys[i - 1] and ys[i] < ys[i + 1] and rng.random() < 0.9:
                for c in range(5):
                    rr = h * (0.008 + c * 0.004)
                    cx, cy = xs[i] + c * h * 0.012, ys[i] + c * h * 0.006
                    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(245, 240, 228), width=max(1, int(h * 0.004)))
        for _ in range(int(w / 30)):
            fx = rng.random() * w
            fy = np.interp(fx, xs, ys) + h * (0.01 + rng.random() * 0.05)
            fr = h * 0.004
            d.ellipse((fx - fr, fy - fr, fx + fr, fy + fr), fill=(245, 240, 228))
    return np.asarray(base).astype(np.float32)


def anime_sky(w, h, rng):
    """Anime sunset: huge clouds lit from below, utility poles and wires, birds."""
    img = gradient(h, w, [(0, "#1b2a6b"), (0.45, "#5a5fbf"), (0.72, "#f29fb5"), (0.88, "#ffcf8a"), (1, "#ffcf8a")])
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = screen(img, "#fff1c7", np.exp(-((yy - 0.9) / 0.1) ** 2) * np.ones((1, w)) * 0.5)
    # Cumulus: clusters of overlapping puffs, flat-ish bottom, lit from below by the sunset
    body = Image.new("L", (w, h), 0)
    lit = Image.new("L", (w, h), 0)
    db, dl = ImageDraw.Draw(body), ImageDraw.Draw(lit)
    size = min(w, h * 2.2)
    for _ in range(4 if w > h * 2 else 5):
        cx, cy = rng.random() * w, h * (0.12 + rng.random() * 0.3)
        cw = size * (0.18 + rng.random() * 0.2)
        for _ in range(14):
            px = cx + (rng.random() - 0.5) * cw
            pr = size * (0.035 + rng.random() * 0.05) * (1 - abs(px - cx) / cw)
            py = cy - pr * (0.2 + rng.random() * 0.6)
            db.ellipse((px - pr, py - pr, px + pr, cy + pr * 0.25), fill=255)
            dl.ellipse((px - pr * 0.9, py - pr * 0.1, px + pr * 0.9, cy + pr * 0.3), fill=255)
    m_body = np.asarray(body.filter(ImageFilter.GaussianBlur(h * 0.006))).astype(np.float32) / 255.0
    m_lit = np.asarray(lit.filter(ImageFilter.GaussianBlur(h * 0.012))).astype(np.float32) / 255.0
    img = blend(img, "#7d6cc4", m_body * 0.95)
    img = blend(img, "#ffd2df", m_lit * m_body * 0.85)
    img = blend(img, "#fff4e8", np.clip(m_lit * m_body - 0.55, 0, 1) * 1.6)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    sil = (24, 20, 48)
    # rooftops
    x = 0.0
    while x < w:
        bw = h * (0.15 + rng.random() * 0.25)
        top = h * (0.86 + rng.random() * 0.06)
        d.rectangle((x, top, x + bw, h), fill=sil)
        if rng.random() < 0.5:
            d.polygon([(x, top), (x + bw / 2, top - h * 0.04), (x + bw, top)], fill=sil)
        x += bw
    # utility poles + wires (catenaries)
    poles = [w * (0.12 + i * 0.36 + (rng.random() - 0.5) * 0.06) for i in range(3)]
    pole_top = h * 0.32
    for px in poles:
        d.rectangle((px - h * 0.008, pole_top, px + h * 0.008, h), fill=sil)
        for k in range(2):
            yk = pole_top + h * (0.04 + k * 0.06)
            d.rectangle((px - h * 0.07, yk, px + h * 0.07, yk + h * 0.012), fill=sil)
    for k in range(4):
        for a, b in zip([-w * 0.3] + poles, poles + [w * 1.3]):
            y_att = pole_top + h * (0.045 + (k // 2) * 0.06)
            off = (k % 2 * 2 - 1) * h * 0.06
            xs = np.linspace(a + off, b + off, 60)
            sag = h * 0.06 * (1 - ((xs - (a + b) / 2) / ((b - a) / 2 + 1e-6)) ** 2)
            d.line(list(zip(xs, y_att + sag)), fill=sil, width=max(1, int(h * 0.003)))
    for _ in range(7):
        bx, by, bs = w * (0.45 + rng.random() * 0.4), h * (0.12 + rng.random() * 0.25), h * (0.008 + rng.random() * 0.01)
        d.line([(bx - bs, by - bs * 0.6), (bx, by), (bx + bs, by - bs * 0.6)], fill=sil, width=max(1, int(h * 0.004)))
    return np.asarray(base).astype(np.float32)


def torii_night(w, h, rng):
    """Shrine at night: vermilion gate, glowing lanterns, mist and moon."""
    img = gradient(h, w, [(0, "#060b24"), (0.6, "#1d1a4a"), (1, "#2c1f3f")])
    img = stars(img, rng, int(w * h / 3000), max_y=0.5)
    moon = Image.new("L", (w, h), 0)
    ImageDraw.Draw(moon).ellipse((w * 0.74, h * 0.1, w * 0.74 + h * 0.18, h * 0.28), fill=255)
    img = screen(img, "#fde6c8", np.asarray(moon.filter(ImageFilter.GaussianBlur(h * 0.08))).astype(np.float32) / 255.0 * 0.5)
    img = blend(img, "#fdf0d8", np.asarray(moon).astype(np.float32) / 255.0)
    img = fill_below(img, ridge(w, rng, h * 0.62, h * 0.08), "#151236")
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = screen(img, "#8b7fd1", np.exp(-((yy - 0.7) / 0.06) ** 2) * np.ones((1, w)) * 0.35)
    img = fill_below(img, np.full(w, h * 0.86), "#0d0a1f")
    base = to_image(img)
    d = ImageDraw.Draw(base)
    gx, gw_, gh = w * 0.3, h * 0.62, h * 0.55
    red, dark = (196, 44, 36), (120, 22, 20)
    top = h * 0.86 - gh
    d.rectangle((gx - gw_ * 0.36, top + gh * 0.12, gx - gw_ * 0.28, h * 0.86), fill=red)
    d.rectangle((gx + gw_ * 0.28, top + gh * 0.12, gx + gw_ * 0.36, h * 0.86), fill=red)
    d.rectangle((gx - gw_ * 0.45, top + gh * 0.24, gx + gw_ * 0.45, top + gh * 0.3), fill=red)
    d.polygon([(gx - gw_ * 0.6, top - gh * 0.02), (gx, top + gh * 0.04), (gx + gw_ * 0.6, top - gh * 0.02),
               (gx + gw_ * 0.55, top + gh * 0.09), (gx - gw_ * 0.55, top + gh * 0.09)], fill=dark)
    d.rectangle((gx - gw_ * 0.5, top + gh * 0.09, gx + gw_ * 0.5, top + gh * 0.13), fill=red)
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    for i in range(6):
        lx = w * (0.55 + i * 0.075) + (rng.random() - 0.5) * h * 0.04
        ly = h * (0.5 + rng.random() * 0.18)
        lr = h * 0.022
        d.line((lx, ly - h * 0.12, lx, ly - lr), fill=(30, 20, 30), width=max(1, int(h * 0.003)))
        g.ellipse((lx - lr, ly - lr * 1.3, lx + lr, ly + lr * 1.3), fill=(255, 140, 60))
    out = _add_glow(np.asarray(base).astype(np.float32), glow, radius=h * 0.05, strength=0.9)
    return vignette(out, 0.35)


def manga_lines(w, h, rng):
    """Manga panel energy: radial speed lines and a halftone dot gradient."""
    img = np.zeros((h, w, 3), dtype=np.float32) + hex_rgb("#0b0b12")
    lines = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(lines)
    cx, cy = w * 0.32, h * 0.5
    radius = math.hypot(w, h)
    for _ in range(260):
        a = rng.random() * 2 * math.pi
        da = 0.002 + rng.random() * 0.01
        r0 = min(w, h) * (0.12 + rng.random() * 0.22)
        p = [(cx + math.cos(a) * r0, cy + math.sin(a) * r0),
             (cx + math.cos(a - da) * radius, cy + math.sin(a - da) * radius),
             (cx + math.cos(a + da) * radius, cy + math.sin(a + da) * radius)]
        d.polygon(p, fill=int(140 + rng.random() * 115))
    img = screen(img, "#f1f1f1", np.asarray(lines).astype(np.float32) / 255.0 * 0.75)
    dots = Image.new("L", (w, h), 0)
    dd = ImageDraw.Draw(dots)
    step = max(10, int(h * 0.03))
    for y in range(0, h + step, step):
        for x in range((y // step) % 2 * step // 2, w + step, step):
            t = np.clip((x / w - 0.45) * 1.8, 0, 1)
            rr = step * 0.5 * t
            if rr > 0.6:
                dd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
    img = blend(img, "#e63946", np.asarray(dots).astype(np.float32) / 255.0 * 0.9)
    return vignette(img, 0.3)


def mecha_hud(w, h, rng):
    """Sci-fi mecha cockpit HUD: rings, ticks, grid and readouts."""
    img = gradient(h, w, [(0, "#03121a"), (1, "#062330")], axis=1)
    hud = _glow_layer(w, h)
    d = ImageDraw.Draw(hud)
    cyan, amber = (0, 220, 255), (255, 176, 59)
    step = max(24, int(h * 0.08))
    for x in range(0, w, step):
        d.line((x, 0, x, h), fill=(0, 60, 80), width=1)
    for y in range(0, h, step):
        d.line((0, y, w, y), fill=(0, 60, 80), width=1)
    cx, cy = w * 0.7, h * 0.5
    for i, rr in enumerate([0.18, 0.28, 0.4, 0.46]):
        R = h * rr * (1.6 if h < w / 2 else 1.0)
        start = rng.random() * 360
        for seg in range(3 + i):
            a0 = start + seg * 360 / (3 + i)
            d.arc((cx - R, cy - R, cx + R, cy + R), a0, a0 + 360 / (3 + i) * (0.4 + rng.random() * 0.4), fill=cyan if i % 2 == 0 else amber, width=max(2, int(h * 0.006)))
    R = h * 0.5 * (1.6 if h < w / 2 else 1.0)
    for k in range(72):
        a = math.radians(k * 5)
        r1 = R * (0.94 if k % 6 else 0.88)
        d.line((cx + math.cos(a) * r1, cy + math.sin(a) * r1, cx + math.cos(a) * R, cy + math.sin(a) * R), fill=cyan, width=1)
    d.line((cx - h * 0.06, cy, cx + h * 0.06, cy), fill=amber, width=2)
    d.line((cx, cy - h * 0.06, cx, cy + h * 0.06), fill=amber, width=2)
    # readout bars on the left
    for i in range(6):
        y = h * (0.2 + i * 0.1)
        L = w * (0.06 + rng.random() * 0.16)
        d.rectangle((w * 0.05, y, w * 0.05 + L, y + h * 0.025), fill=cyan if i % 3 else amber)
        d.rectangle((w * 0.05 + L + h * 0.02, y, w * 0.05 + L + h * 0.05, y + h * 0.025), outline=cyan)
    out = _add_glow(img, hud, radius=h * 0.015, strength=0.6, sharp=0.8)
    scan = (np.arange(h) % 4 == 0).astype(np.float32)[:, None, None]
    return vignette(out * (1 - scan * 0.18), 0.45)


def enchanted_forest(w, h, rng):
    """Magical forest: tree silhouettes, glowing mushrooms and fireflies."""
    img = gradient(h, w, [(0, "#071a24"), (0.6, "#123b4a"), (1, "#1c1236")])
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = screen(img, "#5eead4", np.exp(-((yy - 0.55) / 0.12) ** 2) * np.ones((1, w)) * 0.25)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    for layer, col in enumerate([(14, 46, 58), (9, 30, 40), (4, 14, 20)]):
        x = -20.0
        while x < w + 20:
            tw = h * (0.025 + layer * 0.015) * (0.7 + rng.random() * 0.6)
            crown_y = h * (0.28 + layer * 0.08 + rng.random() * 0.12)
            d.rectangle((x, crown_y, x + tw, h), fill=col)
            for _ in range(7):
                cr = h * (0.07 + layer * 0.035) * (0.6 + rng.random() * 0.6)
                ccx = x + tw / 2 + (rng.random() - 0.5) * cr * 2.2
                ccy = crown_y - cr * (0.2 + rng.random() * 1.1)
                d.ellipse((ccx - cr, ccy - cr, ccx + cr, ccy + cr), fill=col)
            x += tw + h * (0.08 + rng.random() * 0.2) / (layer + 1)
    d.rectangle((0, h * 0.88, w, h), fill=(4, 10, 16))
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    for _ in range(int(w / 70)):
        mx, my = rng.random() * w, h * (0.86 + rng.random() * 0.06)
        mr = h * (0.012 + rng.random() * 0.025)
        c = [(94, 234, 212), (192, 132, 252), (125, 211, 252)][rng.integers(0, 3)]
        d.rectangle((mx - mr * 0.18, my - mr * 0.2, mx + mr * 0.18, my + mr * 1.2), fill=(200, 210, 220))
        g.pieslice((mx - mr, my - mr, mx + mr, my + mr), 180, 360, fill=c)
    for _ in range(int(w * h / 9000)):
        fx, fy, fr = rng.random() * w, h * (0.2 + rng.random() * 0.65), h * (0.002 + rng.random() * 0.004)
        g.ellipse((fx - fr, fy - fr, fx + fr, fy + fr), fill=(255, 236, 140))
    out = _add_glow(np.asarray(base).astype(np.float32), glow, radius=h * 0.02, strength=1.0)
    return vignette(out, 0.35)


def platformer(w, h, rng):
    """16-bit platform game mood: sky, puffy clouds, hills, floating platforms and coins (original layout)."""
    s = 6
    pw, ph = w // s, h // s
    sky = gradient(ph, pw, [(0, "#4aa3ff"), (1, "#a8dcff")])
    sky = np.round(sky / 16) * 16
    im = to_image(sky)
    d = ImageDraw.Draw(im)
    for _ in range(max(3, pw // 40)):
        cx, cy = rng.random() * pw, ph * (0.1 + rng.random() * 0.3)
        for k in range(4):
            rr = ph * (0.05 + rng.random() * 0.04)
            ox = cx + (k - 1.5) * rr * 1.1
            d.ellipse((ox - rr, cy - rr * 0.8, ox + rr, cy + rr * 0.8), fill=(255, 255, 255))
    for i in range(max(3, pw // 50)):
        hx, hr = rng.random() * pw, ph * (0.25 + rng.random() * 0.25)
        d.ellipse((hx - hr * 1.3, ph * 0.82 - hr, hx + hr * 1.3, ph * 0.82 + hr), fill=(76, 175, 80), outline=(46, 125, 50))
    ground = int(ph * 0.82)
    d.rectangle((0, ground, pw, ph), fill=(150, 90, 50))
    d.rectangle((0, ground, pw, ground + 2), fill=(92, 196, 72))
    for x in range(0, pw, 4):
        for y in range(ground + 4, ph, 4):
            if (x // 4 + y // 4) % 2:
                d.rectangle((x, y, x + 1, y + 1), fill=(120, 70, 40))
    for _ in range(max(3, pw // 45)):
        px, py, plen = rng.random() * pw * 0.9, ph * (0.4 + rng.random() * 0.25), int(4 + rng.random() * 5)
        for b in range(plen):
            bx = px + b * 5
            d.rectangle((bx, py, bx + 4, py + 4), fill=(196, 102, 46), outline=(110, 52, 20))
            d.line((bx, py + 2, bx + 4, py + 2), fill=(110, 52, 20))
        for c in range(plen // 2):
            cx = px + c * 9 + 3
            d.ellipse((cx, py - 7, cx + 3, py - 3), fill=(255, 214, 10), outline=(196, 140, 0))
    out = np.asarray(im.resize((w, h), Image.NEAREST)).astype(np.float32)
    return out


def vaporwave(w, h, rng):
    """Vaporwave: sliced sun, checkered floor in perspective, glitch bands."""
    horizon = int(h * 0.6)
    img = gradient(h, w, [(0, "#2d0b4e"), (0.4, "#8a2d8f"), (0.6, "#ff71ce"), (0.601, "#120024"), (1, "#120024")])
    base = to_image(img)
    d = ImageDraw.Draw(base)
    r = h * 0.3
    sun = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sun).ellipse((w * 0.5 - r, horizon - r * 1.2, w * 0.5 + r, horizon + r * 0.8), fill=255)
    sun_col = to_image(gradient(h, w, [(0, "#fffb96"), (0.6, "#ff71ce"), (1, "#ff71ce")]))
    mask = np.asarray(sun).astype(np.float32) / 255.0
    yy = np.arange(h)[:, None]
    for i in range(6):
        y0 = horizon - r * 0.5 + i * r * 0.11
        mask[(yy[:, 0] > y0) & (yy[:, 0] < y0 + 2 + i * 1.5)] = 0
    mask[horizon:] = 0
    arr = np.asarray(base).astype(np.float32)
    arr = arr * (1 - mask[..., None]) + np.asarray(sun_col).astype(np.float32) * mask[..., None]
    # checkered floor in perspective
    floor = np.zeros((h - horizon, w), dtype=np.float32)
    ys = np.arange(1, h - horizon + 1, dtype=np.float32)[:, None]
    xs = (np.arange(w, dtype=np.float32)[None, :] - w / 2)
    z = (h - horizon) / ys
    u = np.floor(xs * z / (h * 0.08))
    v = np.floor(z * 4)
    floor = ((u + v) % 2).astype(np.float32)
    tile_a, tile_b = hex_rgb("#01cdfe"), hex_rgb("#b967ff")
    fade = np.clip(ys / (h - horizon), 0.15, 1)[..., None]
    arr[horizon:] = (tile_a * floor[..., None] + tile_b * (1 - floor[..., None])) * fade * 0.8
    # glitch: shifted bands with RGB split
    for _ in range(6):
        y0 = rng.integers(0, h - 10)
        bh = rng.integers(2, max(3, h // 40))
        dx = rng.integers(-int(w * 0.03), int(w * 0.03))
        arr[y0:y0 + bh] = np.roll(arr[y0:y0 + bh], dx, axis=1)
    arr[..., 0] = np.roll(arr[..., 0], 3, axis=1)
    arr[..., 2] = np.roll(arr[..., 2], -3, axis=1)
    return vignette(arr, 0.3)


def ringed_planet(w, h, rng):
    """Space opera: ringed gas giant, moons and stars."""
    img = gradient(h, w, [(0, "#02030a"), (1, "#0a0820")])
    img = screen(img, "#3b2a8a", np.clip(noise(h, w, rng, octaves=5, base=3) - 0.55, 0, 1) * 0.8)
    img = stars(img, rng, int(w * h / 1500))
    cx, cy, R = w * 0.62, h * 0.55, h * 0.36
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = (xx - cx) / R, (yy - cy) / R
    tilt = 0.35

    def ring_mask(front: bool):
        rx, ry = dx * 1.0, (dy + dx * tilt) * 3.2
        rr = np.sqrt(rx ** 2 + ry ** 2)
        band = ((rr > 1.35) & (rr < 2.15)).astype(np.float32) * (0.55 + 0.45 * np.sin(rr * 30) ** 2)
        side = (dy + dx * tilt) > 0 if front else (dy + dx * tilt) <= 0
        return band * side

    img = blend(img, "#cdb38a", ring_mask(False) * 0.6)
    inside = dx ** 2 + dy ** 2 <= 1
    shade = np.clip(0.25 + 0.95 * (-(dx * 0.7) - dy * 0.4 + np.sqrt(np.clip(1 - dx ** 2 - dy ** 2, 0, 1))) / 1.6, 0.08, 1.1)
    bands = 0.5 + 0.5 * np.sin((dy + dx * tilt) * 14 + noise(h, w, rng, octaves=3, base=4) * 3)
    planet = (hex_rgb("#d9825b") * bands[..., None] + hex_rgb("#7b4b8f") * (1 - bands[..., None])) * shade[..., None]
    img = np.where(inside[..., None], planet, img)
    img = blend(img, "#e8d4a8", ring_mask(True) * 0.75)
    for mx, my, mr in ((0.18, 0.3, 0.05), (0.3, 0.75, 0.025)):
        m = ((xx - w * mx) ** 2 + (yy - h * my) ** 2) <= (h * mr) ** 2
        mshade = np.clip(1 - ((xx - w * mx + h * mr * 0.4) ** 2 + (yy - h * my + h * mr * 0.4) ** 2) / (h * mr * 1.6) ** 2, 0.15, 1)
        img = np.where(m[..., None], hex_rgb("#a9b4c8") * mshade[..., None], img)
    return vignette(img, 0.35)


# --- Pop culture moods, second batch ---

def hyperspace(w, h, rng):
    """Jump to lightspeed: star streaks radiating from the centre."""
    img = np.zeros((h, w, 3), dtype=np.float32) + hex_rgb("#02030b")
    layer = _glow_layer(w, h)
    d = ImageDraw.Draw(layer)
    cx, cy = w * 0.5, h * 0.5
    reach = math.hypot(w, h) * 0.6
    for _ in range(int(w * h / 900)):
        a = rng.random() * 2 * math.pi
        r0 = reach * rng.random() ** 0.7
        ln = r0 * (0.15 + rng.random() * 0.35)
        x0, y0 = cx + math.cos(a) * r0, cy + math.sin(a) * r0
        x1, y1 = cx + math.cos(a) * (r0 + ln), cy + math.sin(a) * (r0 + ln)
        c = [(200, 220, 255), (140, 180, 255), (255, 255, 255), (180, 150, 255)][rng.integers(0, 4)]
        k = 0.3 + 0.7 * (r0 / reach)
        d.line((x0, y0, x1, y1), fill=tuple(int(v * k) for v in c), width=1 if r0 < reach * 0.5 else 2)
    out = _add_glow(img, layer, radius=h * 0.006, strength=0.6)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    core = np.exp(-(((xx - cx) / (h * 0.25)) ** 2 + ((yy - cy) / (h * 0.25)) ** 2))
    out = screen(out, "#9ec5ff", core * 0.55)
    return vignette(out, 0.45)


def _glyph(rng):
    """Random 3x5 glyph bitmap (made-up symbols)."""
    g = rng.random((5, 3)) > 0.45
    g[rng.integers(0, 5), :] = True
    return g


def code_rain(w, h, rng):
    """Falling streams of glowing green glyphs."""
    s = 3
    pw, ph = w // s, h // s
    img = np.zeros((ph, pw, 3), dtype=np.float32) + hex_rgb("#010805")
    col_w, row_h = 4, 6
    for cx in range(0, pw - 3, col_w):
        if rng.random() < 0.35:
            continue
        length = int(rng.integers(6, max(8, ph // row_h)))
        head = int(rng.integers(0, ph // row_h + length))
        for k in range(length):
            row = head - k
            if row < 0 or row * row_h + 5 >= ph:
                continue
            fade = 1 - k / length
            color = hex_rgb("#d8ffe6") if k == 0 else hex_rgb("#22ff88") * (0.25 + 0.75 * fade)
            g = _glyph(rng)
            y0 = row * row_h
            for gy in range(5):
                for gx in range(3):
                    if g[gy, gx]:
                        img[y0 + gy, cx + gx] = color
    out = np.asarray(to_image(img).resize((w, h), Image.NEAREST)).astype(np.float32)
    glow = to_image(out).filter(ImageFilter.GaussianBlur(h * 0.008))
    out = 255 - (255 - out) * (255 - np.asarray(glow).astype(np.float32) * 0.8) / 255
    return vignette(out, 0.4)


def crystal_cave(w, h, rng):
    """Underground cave lit by glowing crystal clusters."""
    img = gradient(h, w, [(0, "#05030d"), (0.6, "#170b2e"), (1, "#0a0518")])
    base = to_image(img)
    d = ImageDraw.Draw(base)
    rock = (12, 8, 22)
    x = 0.0
    while x < w:  # stalactites
        sw = h * (0.04 + rng.random() * 0.08)
        d.polygon([(x, 0), (x + sw, 0), (x + sw / 2, h * (0.08 + rng.random() * 0.25))], fill=rock)
        x += sw * 0.8
    floor = ridge(w, rng, h * 0.9, h * 0.04)
    d.polygon([(0, h)] + [(i, floor[i]) for i in range(0, w, 8)] + [(w, h)], fill=rock)
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    palette = [((90, 230, 255), (200, 250, 255)), ((230, 90, 255), (250, 200, 255)), ((120, 140, 255), (210, 220, 255))]
    for _ in range(max(4, int(w / 160))):
        cx = rng.random() * w
        base_y = floor[min(int(cx), w - 1)] + h * 0.02
        dark, light = palette[rng.integers(0, 3)]
        for _ in range(int(rng.integers(3, 7))):
            ang = math.radians(-90 + (rng.random() - 0.5) * 60)
            ln = h * (0.1 + rng.random() * 0.25)
            wd = ln * 0.16
            tx, ty = cx + math.cos(ang) * ln, base_y + math.sin(ang) * ln
            nx, ny = -math.sin(ang) * wd, math.cos(ang) * wd
            pts = [(cx - nx, base_y - ny), (tx - nx * 0.6, ty - ny * 0.6), (tx + math.cos(ang) * wd * 1.4, ty + math.sin(ang) * wd * 1.4),
                   (tx + nx * 0.6, ty + ny * 0.6), (cx + nx, base_y + ny)]
            g.polygon(pts, fill=dark)
            g.polygon([pts[0], pts[1], pts[2], ((pts[0][0] + pts[4][0]) / 2, (pts[0][1] + pts[4][1]) / 2)], fill=light)
    out = _add_glow(np.asarray(base).astype(np.float32), glow, radius=h * 0.04, strength=0.7)
    return vignette(out, 0.4)


def lava_world(w, h, rng):
    """Volcano world: erupting peak, glowing lava flows and embers."""
    img = gradient(h, w, [(0, "#120404"), (0.5, "#3a0d08"), (0.75, "#6b1a0a"), (1, "#1a0503")])
    smoke = noise(h, w, rng, octaves=5, base=3)
    img = img * (0.7 + 0.5 * smoke[..., None])
    base = to_image(img)
    d = ImageDraw.Draw(base)
    vx, top = w * 0.55, h * 0.3
    d.polygon([(vx - h * 0.9, h * 0.85), (vx - h * 0.08, top), (vx + h * 0.08, top), (vx + h * 0.9, h * 0.85)], fill=(28, 10, 8))
    d.polygon([(0, h * 0.85)] + [(x, h * (0.8 + 0.04 * math.sin(x / w * 9))) for x in range(0, w + 20, 20)] + [(w, h)], fill=(20, 7, 6))
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    for side in (-1, 1):  # lava flows down the slopes
        x, y = vx + side * h * 0.04, top
        pts = [(x, y)]
        while y < h * 0.84:
            y += h * 0.03
            x += side * h * (0.03 + rng.random() * 0.05)
            pts.append((x, y))
        g.line(pts, fill=(255, 120, 20), width=max(4, int(h * 0.022)))
        g.line(pts, fill=(255, 220, 120), width=max(1, int(h * 0.006)))
    g.ellipse((vx - h * 0.09, top - h * 0.05, vx + h * 0.09, top + h * 0.03), fill=(255, 170, 60))
    out = _add_glow(np.asarray(base).astype(np.float32), glow, radius=h * 0.03, strength=0.9)
    # Lava lake: molten orange under a dark crust broken by glowing cracks
    lake_top = int(h * 0.86)
    # noise drawn on the whole frame then cropped: on a thin strip it would be stretched into stripes
    crust = noise(h, w, rng, octaves=5, base=6, stretch=(1.6, 1.0))[lake_top:]
    molten = np.clip((0.5 - crust) * 4, 0, 1)
    edges = np.exp(-((crust - 0.5) / 0.035) ** 2)
    depth = np.linspace(0.6, 1.0, h - lake_top, dtype=np.float32)[:, None]
    lava_rgb = hex_rgb("#ff7a1a")[None, None, :] * (0.6 + 0.4 * molten[..., None]) + hex_rgb("#ffd36e")[None, None, :] * (edges[..., None] * 0.6)
    crust_rgb = hex_rgb("#1c0805")[None, None, :] * np.ones_like(molten)[..., None]
    a = np.clip(molten + edges, 0, 1)[..., None]
    out[lake_top:] = (crust_rgb * (1 - a) + lava_rgb * a) * depth[..., None]
    heat = np.zeros((h, w), dtype=np.float32)
    heat[lake_top:] = a[..., 0]
    heat_glow = np.asarray(Image.fromarray((heat * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(h * 0.04))).astype(np.float32) / 255.0
    out = screen(out, "#ff6a00", heat_glow * 0.8)
    sparks = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(sparks)
    for _ in range(int(w * h / 4000)):
        sx, sy, sr = vx + (rng.random() - 0.5) * w * 0.8, rng.random() * h * 0.8, rng.random() * 1.8 + 0.5
        sd.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=int(120 + rng.random() * 135))
    out = screen(out, "#ffb347", np.asarray(sparks).astype(np.float32) / 255.0)
    return vignette(out, 0.35)


def snow_night(w, h, rng):
    """Winter night: snowy peaks, pine forest, falling snow."""
    img = gradient(h, w, [(0, "#050b1f"), (0.6, "#1b2c55"), (1, "#2a3d66")])
    img = stars(img, rng, int(w * h / 3000), max_y=0.5)
    peaks = ridge(w, rng, h * 0.5, h * 0.14, rough=6)
    yy = np.arange(h, dtype=np.float32)[:, None]
    mask = yy >= peaks[None, :]
    snowcap = np.clip(1 - (yy - peaks[None, :]) / (h * 0.12), 0, 1) * mask
    img = np.where(mask[..., None], hex_rgb("#3b4f7a"), img)
    img = blend(img, "#dde7f7", snowcap * 0.85)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    for layer, col in enumerate([(30, 44, 70), (16, 26, 44)]):
        x = -10.0
        while x < w + 10:
            th = h * (0.18 + layer * 0.08) * (0.6 + rng.random() * 0.6)
            ground = h * (0.8 + layer * 0.08)
            tw = th * 0.35
            for k in range(3):
                t = ground - th + k * th * 0.25
                d.polygon([(x, t), (x - tw * (0.5 + k * 0.2), t + th * 0.4), (x + tw * (0.5 + k * 0.2), t + th * 0.4)], fill=col)
                d.polygon([(x, t), (x - tw * 0.18, t + th * 0.12), (x + tw * 0.18, t + th * 0.12)], fill=(220, 230, 245))
            x += tw * (0.6 + rng.random() * 0.8)
        d.rectangle((0, h * (0.86 + layer * 0.06), w, h), fill=(200, 212, 232) if layer == 0 else (170, 185, 210))
    snow = Image.new("L", (w, h), 0)
    sd = ImageDraw.Draw(snow)
    for _ in range(int(w * h / 1500)):
        sx, sy, sr = rng.random() * w, rng.random() * h, rng.random() * 2.2 + 0.6
        sd.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=int(150 + rng.random() * 105))
    out = screen(np.asarray(base).astype(np.float32), "#ffffff", np.asarray(snow.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32) / 255.0)
    return vignette(out, 0.3)


def deep_sea(w, h, rng):
    """Abyss: light rays from the surface, jellyfish, bubbles, kelp."""
    img = gradient(h, w, [(0, "#0b5a7a"), (0.4, "#063552"), (1, "#020b1a")])
    rays = Image.new("L", (w, h), 0)
    rd = ImageDraw.Draw(rays)
    for _ in range(9):
        x0 = rng.random() * w
        spread = h * (0.05 + rng.random() * 0.1)
        rd.polygon([(x0, 0), (x0 + spread, 0), (x0 + spread * 3 - h * 0.3, h), (x0 + spread * 2 - h * 0.4, h)], fill=int(40 + rng.random() * 50))
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = screen(img, "#a8e6ff", np.asarray(rays.filter(ImageFilter.GaussianBlur(h * 0.03))).astype(np.float32) / 255.0 * (1 - yy) * 0.8)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    floor = ridge(w, rng, h * 0.88, h * 0.05)
    d.polygon([(0, h)] + [(i, floor[i]) for i in range(0, w, 8)] + [(w, h)], fill=(3, 12, 22))
    for _ in range(int(w / 60)):  # kelp
        kx = rng.random() * w
        ky = floor[min(int(kx), w - 1)]
        pts = [(kx + math.sin(t / 3 + kx) * h * 0.02, ky - t * h * 0.03) for t in range(int(6 + rng.random() * 8))]
        d.line(pts, fill=(6, 40, 40), width=max(2, int(h * 0.01)))
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    for _ in range(max(3, int(w / 300))):
        jx, jy, jr = rng.random() * w, h * (0.25 + rng.random() * 0.45), h * (0.03 + rng.random() * 0.04)
        c = [(255, 120, 200), (150, 120, 255), (120, 230, 255)][rng.integers(0, 3)]
        g.pieslice((jx - jr, jy - jr, jx + jr, jy + jr), 180, 360, fill=tuple(int(v * 0.8) for v in c))
        for t in range(5):
            tx = jx - jr * 0.7 + t * jr * 0.35
            g.line([(tx + math.sin(k / 2 + t) * jr * 0.15, jy + k * jr * 0.35) for k in range(6)], fill=c, width=max(1, int(h * 0.003)))
    out = _add_glow(np.asarray(base).astype(np.float32), glow, radius=h * 0.03, strength=0.8)
    bub = Image.new("L", (w, h), 0)
    bd = ImageDraw.Draw(bub)
    for _ in range(int(w * h / 6000)):
        bx, by, br = rng.random() * w, rng.random() * h * 0.85, rng.random() * h * 0.008 + 1
        bd.ellipse((bx - br, by - br, bx + br, by + br), outline=int(120 + rng.random() * 100))
    out = screen(out, "#d8f6ff", np.asarray(bub).astype(np.float32) / 255.0 * 0.7)
    return vignette(out, 0.4)


def blood_moon(w, h, rng):
    """Gothic night: huge red moon, castle silhouette with lit windows, bats."""
    img = gradient(h, w, [(0, "#0a0205"), (0.55, "#2a0710"), (1, "#120306")])
    moon = Image.new("L", (w, h), 0)
    mr = h * 0.28
    mx, my = w * 0.62, h * 0.4
    ImageDraw.Draw(moon).ellipse((mx - mr, my - mr, mx + mr, my + mr), fill=255)
    m = np.asarray(moon).astype(np.float32) / 255.0
    img = screen(img, "#ff3b3b", np.asarray(moon.filter(ImageFilter.GaussianBlur(h * 0.1))).astype(np.float32) / 255.0 * 0.5)
    tex = noise(h, w, rng, octaves=4, base=6)
    img = img * (1 - m[..., None]) + (hex_rgb("#c8202a") * (0.75 + 0.35 * tex[..., None])) * m[..., None]
    base = to_image(img)
    d = ImageDraw.Draw(base)
    sil = (8, 2, 5)
    d.polygon([(0, h)] + [(x, h * (0.82 + 0.05 * math.sin(x / w * 7 + 1))) for x in range(0, w + 20, 20)] + [(w, h)], fill=sil)
    cx = w * 0.42
    towers = [(-0.22, 0.22, 0.05), (-0.12, 0.34, 0.04), (0.0, 0.46, 0.06), (0.12, 0.3, 0.045), (0.2, 0.2, 0.04)]
    glow = _glow_layer(w, h)
    g = ImageDraw.Draw(glow)
    d.rectangle((cx - h * 0.3, h * 0.68, cx + h * 0.3, h), fill=sil)
    for ox, th, tw in towers:
        tx, tw_px = cx + ox * h * 1.4, h * tw
        top = h * 0.82 - h * th
        d.rectangle((tx - tw_px, top, tx + tw_px, h), fill=sil)
        d.polygon([(tx - tw_px * 1.3, top), (tx, top - h * 0.1), (tx + tw_px * 1.3, top)], fill=sil)
        for k in range(int(th * 10)):
            if rng.random() < 0.5:
                wy = top + h * 0.03 + k * h * 0.045
                g.rectangle((tx - tw_px * 0.2, wy, tx + tw_px * 0.2, wy + h * 0.02), fill=(255, 180, 80))
    out = _add_glow(np.asarray(base).astype(np.float32), glow, radius=h * 0.015, strength=0.7)
    b = to_image(out)
    bd = ImageDraw.Draw(b)
    for _ in range(9):  # bats
        bx, by, bs = mx + (rng.random() - 0.5) * mr * 3, my + (rng.random() - 0.5) * mr * 1.6, h * (0.012 + rng.random() * 0.012)
        bd.polygon([(bx - bs * 2, by - bs * 0.4), (bx - bs, by), (bx - bs * 0.4, by - bs * 0.2), (bx, by + bs * 0.3),
                    (bx + bs * 0.4, by - bs * 0.2), (bx + bs, by), (bx + bs * 2, by - bs * 0.4), (bx, by - bs * 0.1)], fill=sil)
    return vignette(np.asarray(b).astype(np.float32), 0.4)


def block_world(w, h, rng):
    """Sandbox game mood: terrain made of cubes, trees, flat clouds (generic blocks)."""
    s = 4
    pw, ph = w // s, h // s
    bs = 8  # block size in low-res pixels
    cols, rows = pw // bs + 1, ph // bs + 1
    img = gradient(ph, pw, [(0, "#6fb7ff"), (1, "#bfe3ff")])
    img = np.round(img / 10) * 10
    heights = np.clip((ridge(cols, rng, rows * 0.55, rows * 0.15, rough=4)).astype(int), 2, rows - 2)
    grass, dirt, stone = hex_rgb("#5fae3c"), hex_rgb("#8a5a33"), hex_rgb("#7d7d84")

    def block(cx, cy, color):
        y0, x0 = cy * bs, cx * bs
        if y0 < 0 or x0 < 0 or y0 >= ph or x0 >= pw:
            return
        tile = np.ones((bs, bs, 1), dtype=np.float32) * color
        tile[:, :] *= (0.92 + 0.12 * rng.random((bs, bs, 1)))
        tile[0, :] *= 1.15
        tile[-1, :] *= 0.75
        tile[:, -1] *= 0.8
        img[y0:y0 + bs, x0:x0 + bs] = tile[: ph - y0, : pw - x0]

    for cx in range(cols):
        top = rows - heights[cx]
        for cy in range(top, rows):
            block(cx, cy, grass if cy == top else dirt if cy < top + 3 else stone)
        if rng.random() < 0.12 and top > 4:
            for k in range(1, 4):
                block(cx, top - k, hex_rgb("#6b4a2b"))
            for lx in range(cx - 1, cx + 2):
                for ly in range(top - 6, top - 3):
                    if 0 <= lx < cols:
                        block(lx, ly, hex_rgb("#3f8f2f"))
    for _ in range(max(2, cols // 12)):
        cy, cx, ln = int(rng.integers(1, 4)), int(rng.integers(0, cols)), int(rng.integers(3, 7))
        for k in range(ln):
            y0, x0 = cy * bs, (cx + k) * bs
            if x0 < pw:
                img[y0:y0 + bs // 2, x0:x0 + bs] = 245
    img[bs: bs * 2, pw - bs * 4: pw - bs * 3] = hex_rgb("#fff3b0")
    return np.asarray(to_image(img).resize((w, h), Image.NEAREST)).astype(np.float32)


def desert_ruins(w, h, rng):
    """Adventure game sunset: pyramids, broken columns, dunes."""
    img = gradient(h, w, [(0, "#2b1645"), (0.4, "#b4452e"), (0.65, "#f39a3d"), (1, "#f6c27a")])
    sun = Image.new("L", (w, h), 0)
    ImageDraw.Draw(sun).ellipse((w * 0.2, h * 0.38, w * 0.2 + h * 0.3, h * 0.68), fill=255)
    img = screen(img, "#ffe7a3", np.asarray(sun.filter(ImageFilter.GaussianBlur(h * 0.06))).astype(np.float32) / 255.0 * 0.7)
    img = blend(img, "#fff1c4", np.asarray(sun).astype(np.float32) / 255.0 * 0.9)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    for px, ph_, col in ((0.55, 0.42, (122, 54, 40)), (0.72, 0.3, (140, 66, 46)), (0.42, 0.24, (150, 74, 52))):
        x = w * px
        d.polygon([(x - h * ph_ * 1.1, h * 0.78), (x, h * (0.78 - ph_)), (x + h * ph_ * 1.1, h * 0.78)], fill=col)
        d.polygon([(x, h * (0.78 - ph_)), (x + h * ph_ * 1.1, h * 0.78), (x + h * ph_ * 0.2, h * 0.78)], fill=tuple(int(c * 0.75) for c in col))
    xs = np.arange(0, w + 10, 10)
    for i, col in enumerate([(176, 96, 52), (150, 78, 42)]):
        ys = h * (0.76 + i * 0.08) + np.sin(xs / w * (5 + i * 3) + rng.random() * 6) * h * 0.03
        d.polygon([(0, h)] + list(zip(xs, ys)) + [(w, h)], fill=col)
    for k in range(5):  # broken columns in the foreground
        cx = w * (0.05 + k * 0.1 + rng.random() * 0.04)
        ch = h * (0.12 + rng.random() * 0.18)
        cw = h * 0.035
        d.rectangle((cx - cw, h * 0.92 - ch, cx + cw, h * 0.92), fill=(70, 34, 24))
        d.rectangle((cx - cw * 1.4, h * 0.92 - ch - h * 0.015, cx + cw * 1.4, h * 0.92 - ch), fill=(70, 34, 24))
    return vignette(np.asarray(base).astype(np.float32), 0.3)


def lofi_rain(w, h, rng):
    """Lo-fi study night: rainy window over a blurred city, warm lamp."""
    outside = gradient(h, w, [(0, "#141a3a"), (0.6, "#3b3a6b"), (1, "#5a3d5c")])
    bokeh = Image.new("RGB", (w, h), (0, 0, 0))
    bd = ImageDraw.Draw(bokeh)
    for _ in range(90):
        r = h * (0.01 + rng.random() * 0.04)
        x, y = rng.random() * w, h * (0.4 + rng.random() * 0.55)
        c = [(255, 170, 90), (110, 170, 255), (255, 110, 160), (255, 220, 140)][rng.integers(0, 4)]
        k = 0.3 + rng.random() * 0.6
        bd.ellipse((x - r, y - r, x + r, y + r), fill=tuple(int(v * k) for v in c))
    bokeh = bokeh.filter(ImageFilter.GaussianBlur(h * 0.012))
    img = 255 - (255 - outside) * (255 - np.asarray(bokeh).astype(np.float32)) / 255
    drops = Image.new("L", (w, h), 0)
    dd = ImageDraw.Draw(drops)
    for _ in range(int(w * h / 900)):
        x, y, r = rng.random() * w, rng.random() * h, rng.random() * h * 0.006 + 1
        dd.ellipse((x - r, y - r * 1.2, x + r, y + r * 1.2), fill=int(70 + rng.random() * 90))
        if rng.random() < 0.06:
            dd.line((x, y, x + (rng.random() - 0.5) * 4, y + h * (0.05 + rng.random() * 0.15)), fill=70, width=max(1, int(r * 0.6)))
    img = screen(img, "#cfe0ff", np.asarray(drops).astype(np.float32) / 255.0 * 0.6)
    base = to_image(img)
    d = ImageDraw.Draw(base)
    frame = (20, 14, 22)
    fw = max(6, int(h * 0.03))
    d.rectangle((0, 0, w, fw), fill=frame)
    d.rectangle((0, h - fw * 2, w, h), fill=frame)
    for x in (0, w * 0.5 - fw / 2, w - fw):
        d.rectangle((x, 0, x + fw, h), fill=frame)
    d.rectangle((0, h * 0.5 - fw / 2, w, h * 0.5 + fw / 2), fill=frame)
    out = np.asarray(base).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    lamp = np.exp(-(((xx - w * 0.92) / (h * 0.6)) ** 2 + ((yy - h * 0.95) / (h * 0.5)) ** 2))
    out = screen(out, "#ffb36b", lamp * 0.45)
    return vignette(out, 0.35)


def galaxy_spiral(w, h, rng):
    """Spiral galaxy with a bright core."""
    img = np.zeros((h, w, 3), dtype=np.float32) + hex_rgb("#02020a")
    img = stars(img, rng, int(w * h / 1400))
    layer = _glow_layer(w, h)
    d = ImageDraw.Draw(layer)
    cx, cy = w * 0.5, h * 0.5
    scale = min(w * 0.45, h * 0.9)
    for arm in range(2):
        for _ in range(9000 if w * h > 1e6 else 6000):
            t = rng.random() ** 0.8 * 3.4
            a = t * 2.1 + arm * math.pi + rng.normal() * 0.28
            r = (t / 3.4) * scale * (1 + rng.normal() * 0.08)
            x, y = cx + math.cos(a) * r, cy + math.sin(a) * r * 0.45
            mix = t / 3.4
            c = (int(255 - 120 * mix), int(220 - 90 * mix), int(180 + 60 * mix))
            if rng.random() < 0.08:
                c = (255, 120, 190)
            sz = 1 + (rng.random() < 0.1)
            d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=c)
    out = _add_glow(img, layer, radius=h * 0.012, strength=0.9, sharp=0.7)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    core = np.exp(-(((xx - cx) / (scale * 0.12)) ** 2 + ((yy - cy) / (scale * 0.06)) ** 2))
    out = screen(out, "#fff1d0", core)
    return vignette(out, 0.4)


def storm(w, h, rng):
    """Thunderstorm over a dark sea: heavy clouds, lightning bolt, rain."""
    img = gradient(h, w, [(0, "#07090f"), (0.6, "#1a2233"), (1, "#0b0f18")])
    clouds = noise(h, w, rng, octaves=6, base=3, stretch=(0.6, 1.4))
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    img = blend(img, "#2d3850", np.clip((clouds - 0.4) * 2, 0, 1) * np.clip(1 - yy * 1.4, 0, 1))
    bolt = _glow_layer(w, h)
    d = ImageDraw.Draw(bolt)
    for b in range(2 if w > h * 2 else 1):
        x, y = w * (0.35 + b * 0.35 + (rng.random() - 0.5) * 0.1), 0.0
        pts = [(x, y)]
        while y < h * 0.72:
            y += h * (0.04 + rng.random() * 0.05)
            x += (rng.random() - 0.5) * h * 0.12
            pts.append((x, y))
            if rng.random() < 0.25:  # branch
                bx, by = x, y
                branch = [(bx, by)]
                for _ in range(3):
                    by += h * 0.04
                    bx += (rng.random() - 0.3) * h * 0.08
                    branch.append((bx, by))
                d.line(branch, fill=(170, 190, 255), width=max(1, int(h * 0.004)))
        d.line(pts, fill=(235, 240, 255), width=max(2, int(h * 0.007)))
    light = np.asarray(bolt.filter(ImageFilter.GaussianBlur(h * 0.25))).astype(np.float32) / 255.0
    img = img + light * 120
    img = _add_glow(img, bolt, radius=h * 0.02, strength=0.9)
    sea = h * 0.74
    img = fill_below(img, np.full(w, sea), "#0a0f1a")
    xs = np.arange(w, dtype=np.float32)
    for k in range(6):
        yk = sea + h * 0.02 + k * h * 0.04
        crest = np.exp(-((np.arange(h)[:, None] - (yk + np.sin(xs / (30 + k * 10) + k) * h * 0.006)[None, :]) / 1.5) ** 2)
        img = screen(img, "#5c6f94", crest * 0.35)
    rain = Image.new("L", (w, h), 0)
    r = ImageDraw.Draw(rain)
    for _ in range(int(w * h / 1000)):
        x0, y0, ln = rng.random() * w, rng.random() * h, h * (0.03 + rng.random() * 0.05)
        r.line((x0, y0, x0 - ln * 0.3, y0 + ln), fill=int(50 + rng.random() * 70), width=1)
    img = screen(img, "#aab8d6", np.asarray(rain).astype(np.float32) / 255.0 * 0.6)
    return vignette(img, 0.4)


THEMES = {
    "aurora": aurora,
    "nebula": nebula,
    "synthwave": synthwave,
    "mountains": mountains,
    "ocean": ocean,
    "lowpoly": lowpoly,
    "topo": topo,
    "pixel": pixel_city,
    "sakura": sakura,
    "ember": ember,
    "circuit": circuit,
    "dunes": dunes,
    # background only
    "starfield": starfield,
    "hexgrid": hexgrid,
    "forest": forest,
    "bokeh": bokeh,
    "flow": flow,
    "dotgrid": dotgrid,
    # pop culture moods (banner and background)
    "neon_city": neon_city,
    "pixel_dungeon": pixel_dungeon,
    "arcade": arcade,
    "great_wave": great_wave,
    "anime_sky": anime_sky,
    "torii": torii_night,
    "manga": manga_lines,
    "mecha_hud": mecha_hud,
    "enchanted_forest": enchanted_forest,
    "platformer": platformer,
    "vaporwave": vaporwave,
    "planet": ringed_planet,
    "hyperspace": hyperspace,
    "code_rain": code_rain,
    "crystal_cave": crystal_cave,
    "lava_world": lava_world,
    "snow_night": snow_night,
    "deep_sea": deep_sea,
    "blood_moon": blood_moon,
    "block_world": block_world,
    "desert_ruins": desert_ruins,
    "lofi_rain": lofi_rain,
    "galaxy": galaxy_spiral,
    "storm": storm,
}
BANNER_THEMES = [
    "aurora", "nebula", "synthwave", "mountains", "ocean", "lowpoly", "topo", "pixel", "sakura", "ember", "circuit", "dunes",
    "neon_city", "pixel_dungeon", "arcade", "great_wave", "anime_sky", "torii", "manga", "mecha_hud", "enchanted_forest", "platformer", "vaporwave", "planet",
    "hyperspace", "code_rain", "crystal_cave", "lava_world", "snow_night", "deep_sea", "blood_moon", "block_world", "desert_ruins", "lofi_rain", "galaxy", "storm",
]
# Page backgrounds, darkened and softened behind the content
BACKGROUND_THEMES = [
    "nebula", "aurora", "topo", "circuit", "pixel", "dunes", "ocean", "lowpoly",
    "starfield", "hexgrid", "forest", "bokeh", "flow", "dotgrid", "synthwave", "mountains", "sakura", "ember",
    "neon_city", "pixel_dungeon", "arcade", "great_wave", "anime_sky", "torii", "manga", "mecha_hud", "enchanted_forest", "platformer", "vaporwave", "planet",
    "hyperspace", "code_rain", "crystal_cave", "lava_world", "snow_night", "deep_sea", "blood_moon", "block_world", "desert_ruins", "lofi_rain", "galaxy", "storm",
]


def main():
    (OUT / "banners").mkdir(parents=True, exist_ok=True)
    (OUT / "backgrounds").mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None  # optional: regenerate some themes only
    for i, name in enumerate(BANNER_THEMES):
        if only and name not in only:
            continue
        img = to_image(THEMES[name](*BANNER, np.random.default_rng(100 + i)))
        img.save(OUT / "banners" / f"{name}.webp", "WEBP", quality=84, method=6)
        img.resize((400, 100), Image.LANCZOS).save(OUT / "banners" / f"{name}_thumb.webp", "WEBP", quality=80)
        print("banner", name)
    for i, name in enumerate(BACKGROUND_THEMES):
        if only and name not in only:
            continue
        arr = THEMES[name](*BACKGROUND, np.random.default_rng(500 + i))
        img = to_image(arr * 0.55).filter(ImageFilter.GaussianBlur(1.2))
        img.save(OUT / "backgrounds" / f"{name}.webp", "WEBP", quality=80, method=6)
        img.resize((384, 216), Image.LANCZOS).save(OUT / "backgrounds" / f"{name}_thumb.webp", "WEBP", quality=80)
        print("background", name)


if __name__ == "__main__":
    main()
