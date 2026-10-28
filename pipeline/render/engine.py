"""Frame-level drawing primitives for the programmatic motion-graphics renderer.

Everything is drawn at SS x resolution and downscaled for anti-aliasing.
Coordinates passed to helpers are in *output* pixels (1080x1920); helpers scale.
"""
from __future__ import annotations

import json
import math
import random
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
BRAND = json.loads((ROOT / "config/brand.json").read_text(encoding="utf-8"))
W = BRAND["video"]["width"]
H = BRAND["video"]["height"]
FPS = BRAND["video"]["fps"]
SAFE = BRAND["safe_area"]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


C = {k: hex_rgb(v) for k, v in BRAND["colors"].items()}


# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x):
    x = clamp(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def seg(t, start, dur):
    """Progress 0..1 of a sub-animation starting at `start` seconds lasting `dur`."""
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def lerp(a, b, x):
    return a + (b - a) * x


def mix(c1, c2, x):
    return tuple(int(lerp(a, b, clamp(x))) for a, b in zip(c1, c2))


# ---------------------------------------------------------------- fonts
@lru_cache(maxsize=256)
def font(size: int, family: str = "heavy", weight: int = 900) -> ImageFont.FreeTypeFont:
    path = ROOT / BRAND["fonts"][family]
    f = ImageFont.truetype(str(path), size)
    if family == "sans":
        f.set_variation_by_axes([weight])
    return f


class Canvas:
    def __init__(self, ss: int = 2):
        self.ss = ss
        self.img = Image.new("RGBA", (W * ss, H * ss), C["bg"] + (255,))
        self.d = ImageDraw.Draw(self.img)

    def s(self, v):
        return v * self.ss

    def pt(self, x, y):
        return (x * self.ss, y * self.ss)

    def font(self, size, family="heavy", weight=900):
        return font(int(size * self.ss), family, weight)

    # -- shapes
    def circle(self, x, y, r, fill=None, outline=None, width=0):
        if r <= 0:
            return
        s = self.ss
        self.d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=fill, outline=outline,
                       width=int(width * s))

    def line(self, pts, fill, width=4):
        self.d.line([self.pt(*p) for p in pts], fill=fill, width=int(width * self.ss), joint="curve")

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=0, radius=0):
        s = self.ss
        self.d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=radius * s, fill=fill,
                                 outline=outline, width=int(width * s))

    def polygon(self, pts, fill=None, outline=None, width=1):
        if len(pts) < 3:
            return
        self.d.polygon([self.pt(*p) for p in pts], fill=fill, outline=outline, width=max(1, int(width * self.ss)))

    def paste(self, layer: Image.Image, x: int = 0, y: int = 0):
        self.img.alpha_composite(layer, (int(x * self.ss), int(y * self.ss)))

    def overlay(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        layer = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        return layer, ImageDraw.Draw(layer)

    def glow(self, draw_fn, radius=18, strength=1.0):
        """Soft glow: draw_fn(draw, k) paints at quarter resolution (k = px per output px), blurred, added on top."""
        q = 4
        small = Image.new("RGBA", (self.img.width // q, self.img.height // q), (0, 0, 0, 0))
        draw_fn(ImageDraw.Draw(small), self.ss / q)
        bb = small.getbbox()
        if not bb:
            return
        pad = int(radius * self.ss / q * 2.5) + 2
        bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(small.width, bb[2] + pad), min(small.height, bb[3] + pad))
        crop = small.crop(bb).filter(ImageFilter.GaussianBlur(radius / q * self.ss))
        if strength != 1.0:
            crop.putalpha(crop.getchannel("A").point(lambda v: min(255, int(v * strength))))
        crop = crop.resize(((bb[2] - bb[0]) * q, (bb[3] - bb[1]) * q), Image.BILINEAR)
        self.img.alpha_composite(crop, (bb[0] * q, bb[1] * q))

    # -- text
    def text_size(self, text, size, family="heavy", weight=900):
        f = self.font(size, family, weight)
        b = f.getbbox(text)
        return (b[2] - b[0]) / self.ss, (b[3] - b[1]) / self.ss

    def text(self, x, y, text, size, fill, family="heavy", weight=900, anchor="mm", stroke=0,
             stroke_fill=(0, 0, 0), alpha=1.0):
        if alpha <= 0 or not text:
            return
        f = self.font(size, family, weight)
        if alpha >= 1:
            self.d.text(self.pt(x, y), text, font=f, fill=fill, anchor=anchor, stroke_width=int(stroke * self.ss),
                        stroke_fill=stroke_fill)
            return
        # alpha text: draw into a layer just big enough for the glyphs
        bb = self.d.textbbox(self.pt(x, y), text, font=f, anchor=anchor, stroke_width=int(stroke * self.ss))
        pad = 4
        x0, y0 = int(bb[0]) - pad, int(bb[1]) - pad
        layer = Image.new("RGBA", (int(bb[2]) - x0 + pad, int(bb[3]) - y0 + pad), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((self.pt(x, y)[0] - x0, self.pt(x, y)[1] - y0), text, font=f, fill=fill + (255,),
                                   anchor=anchor, stroke_width=int(stroke * self.ss), stroke_fill=stroke_fill)
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
        cx0, cy0 = max(0, -x0), max(0, -y0)
        self.img.alpha_composite(layer.crop((cx0, cy0, layer.width, layer.height)), (x0 + cx0, y0 + cy0))

    def rich_line(self, cx, y, runs, size, family="heavy", stroke=0, alpha=1.0, scale=1.0):
        """runs: list of (text, rgb). Rendered centered at cx."""
        size = size * scale
        widths = [self.text_size(t, size, family)[0] if t.strip() else self.font(size, family).getlength(t) / self.ss
                  for t, _ in runs]
        total = sum(widths)
        x = cx - total / 2
        for (t, col), w in zip(runs, widths):
            self.text(x, y, t, size, col, family=family, anchor="lm", stroke=stroke, alpha=alpha)
            x += w

    def finish(self) -> Image.Image:
        out = self.img.convert("RGB")
        if self.ss != 1:
            out = out.reduce(self.ss)
        return out


# ---------------------------------------------------------------- text layout
def split_emphasis(text: str, emphasis: list[str], base, hi) -> list[tuple[str, tuple]]:
    runs: list[tuple[str, tuple]] = []
    i = 0
    while i < len(text):
        hit = None
        for e in sorted(emphasis, key=len, reverse=True):
            if e and text.startswith(e, i):
                hit = e
                break
        if hit:
            runs.append((hit, hi))
            i += len(hit)
        else:
            if runs and runs[-1][1] == base:
                runs[-1] = (runs[-1][0] + text[i], base)
            else:
                runs.append((text[i], base))
            i += 1
    return runs




BREAK_AFTER = "、。！？!? "


def wrap_jp(text: str, max_chars: int) -> list[str]:
    """Wrap Japanese only at natural break points: after 、。！？ or at an explicit '|' hint
    written in the script (e.g. "巨大な満ち引きに|振り回される"). Chunks are packed greedily;
    a chunk longer than max_chars stays on its own line rather than being cut mid-word."""
    lines: list[str] = []
    for para in text.split("\n"):
        chunks, cur = [], ""
        for ch in para:
            if ch == "|":
                chunks.append(cur)
                cur = ""
                continue
            cur += ch
            if ch in BREAK_AFTER:
                chunks.append(cur)
                cur = ""
        if cur:
            chunks.append(cur)
        line = ""
        for c in (c for c in chunks if c.strip()):
            if line and len(line) + len(c) > max_chars:
                lines.append(line)
                line = c
            else:
                line += c
        if line:
            lines.append(line)
    return [l.strip() for l in lines if l.strip()]


def strip_hints(text: str) -> str:
    return text.replace("|", "")


def draw_subtitle(cv: Canvas, text: str, emphasis: list[str], p_in: float, alpha: float = 1.0):
    cfg = BRAND["subtitle"]
    size = cfg["font_size"]
    lines = wrap_jp(text, cfg["max_chars_per_line"])
    lh = size * 1.32
    cy = cfg["center_y"]
    top = cy - lh * len(lines) / 2
    usable_l, usable_r = SAFE["left"], W - SAFE["right"]
    cx = (usable_l + usable_r) / 2
    maxw = max(cv.text_size(l, size)[0] for l in lines) if lines else 0
    a = ease_out(p_in) * alpha
    if a <= 0:
        return
    s = cv.ss
    pad = 28
    bx0, by0 = int((cx - maxw / 2 - pad) * s), int((top - 14) * s)
    bx1, by1 = int((cx + maxw / 2 + pad) * s), int((top + lh * len(lines) + 10) * s)
    box = Image.new("RGBA", (bx1 - bx0, by1 - by0), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([0, 0, bx1 - bx0 - 1, by1 - by0 - 1], radius=22 * s,
                                          fill=(0, 0, 0, int(cfg["box_alpha"] * a)))
    cv.img.alpha_composite(box, (bx0, by0))
    rise = (1 - ease_out(p_in)) * 18
    for i, l in enumerate(lines):
        runs = split_emphasis(l, emphasis, C["white"], C["yellow"])
        cv.rich_line(cx, top + lh * (i + 0.5) + rise, runs, size, stroke=3, alpha=a)


# ---------------------------------------------------------------- background
@lru_cache(maxsize=4)
def starfield(ss: int, seed: int = 7) -> Image.Image:
    rnd = random.Random(seed)
    img = Image.new("RGBA", (W * ss, int(H * 1.15) * ss), C["bg"] + (255,))
    d = ImageDraw.Draw(img)
    # radial vignette glow
    glow = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(40, 0, -1):
        r = i * 9
        a = int(4 + (40 - i) * 0.35)
        gd.ellipse([W / 8 - r, H / 8 - r * 1.3, W / 8 + r, H / 8 + r * 1.3], fill=C["emerald_dark"] + (a,))
    glow = glow.filter(ImageFilter.GaussianBlur(30)).resize((W * ss, H * ss), Image.BILINEAR)
    img.alpha_composite(glow, (0, int(H * 0.05) * ss))
    for _ in range(420):
        x, y = rnd.random() * W, rnd.random() * H * 1.15
        r = rnd.choice([0.8, 1.0, 1.2, 1.6, 2.2])
        b = rnd.randint(90, 230)
        d.ellipse([(x - r) * ss, (y - r) * ss, (x + r) * ss, (y + r) * ss], fill=(b, b, b, 255))
    # faint grid (composited so the low alpha actually blends)
    grid = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(grid)
    for gx in range(0, W, 90):
        gd2.line([(gx * ss, 0), (gx * ss, img.height)], fill=C["emerald"] + (22,), width=ss)
    for gy in range(0, int(H * 1.15), 90):
        gd2.line([(0, gy * ss), (img.width, gy * ss)], fill=C["emerald"] + (22,), width=ss)
    img.alpha_composite(grid)
    return img


def draw_background(cv: Canvas, t_global: float):
    sf = starfield(cv.ss)
    off = int((t_global * 6) % (H * 0.15)) * cv.ss
    cv.img.paste(sf.crop((0, off, W * cv.ss, off + H * cv.ss)), (0, 0))


def draw_branding(cv: Canvas, t: float):
    cv.text(SAFE["left"] + 4, SAFE["top"] - 70, BRAND["series_name"], 30, C["emerald"], family="sans", weight=800,
            anchor="lm", alpha=0.9)


def shake(t: float, amp: float, freq: float = 23.0) -> tuple[float, float]:
    return (math.sin(t * freq) * amp, math.cos(t * freq * 1.3) * amp)
