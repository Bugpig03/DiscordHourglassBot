"""Generate the profile image gallery: banners and page backgrounds, all original procedural art.

Each theme is drawn with numpy/Pillow (no third-party images, nothing to license). Banners are 1600x400,
backgrounds 1920x1080 (darker and softer so text stays readable), each with a small thumbnail for the picker.

Usage (from web/, requires Pillow and numpy):
    python scripts/make_profile_gallery.py app/static/images/profile
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
}
# Page backgrounds: the calmer themes, darkened and softened behind the content
BACKGROUND_THEMES = ["nebula", "aurora", "topo", "circuit", "pixel", "dunes", "ocean", "lowpoly"]


def main():
    (OUT / "banners").mkdir(parents=True, exist_ok=True)
    (OUT / "backgrounds").mkdir(parents=True, exist_ok=True)
    for i, (name, fn) in enumerate(THEMES.items()):
        img = to_image(fn(*BANNER, np.random.default_rng(100 + i)))
        img.save(OUT / "banners" / f"{name}.webp", "WEBP", quality=84, method=6)
        img.resize((400, 100), Image.LANCZOS).save(OUT / "banners" / f"{name}_thumb.webp", "WEBP", quality=80)
        print("banner", name)
    for i, name in enumerate(BACKGROUND_THEMES):
        arr = THEMES[name](*BACKGROUND, np.random.default_rng(500 + i))
        img = to_image(arr * 0.55).filter(ImageFilter.GaussianBlur(1.2))
        img.save(OUT / "backgrounds" / f"{name}.webp", "WEBP", quality=80, method=6)
        img.resize((384, 216), Image.LANCZOS).save(OUT / "backgrounds" / f"{name}_thumb.webp", "WEBP", quality=80)
        print("background", name)


if __name__ == "__main__":
    main()
