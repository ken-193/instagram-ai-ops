"""On-screen text layer for 世界の仕様外 (drawn on the rendered frames at 1080x1920 before encoding).

Layout (inside the Reels safe area: top 220 px / bottom 420 px are covered by the app UI):
  top     : series question  (e.g. 「もしも 夜 がなくなったら？」, keyword in accent colour)
            clock label  「夜が消えてから ▶▶×60」  + big clock 「0日 21:00」 with a green underline
            place label 「日本・住宅街（夜9時）」
  middle  : headline (1 line, big) + sub (1–2 lines, smaller) — fade/slide in
Per-scene settings live in project.json scenes[].hud.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT_HEAVY = ROOT / "assets/fonts/NotoSansJP-VF.ttf"
W, H = 1080, 1920
WHITE = (255, 255, 255)
ACCENT = (197, 48, 48)      # brand terracotta
GREEN = (47, 133, 90)       # brand deep green
MUTED = (230, 230, 225)


@lru_cache(maxsize=32)
def font(size: int, weight: int = 800) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT_HEAVY), size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _runs(text: str, keyword: str | None):
    if not keyword or keyword not in text:
        return [(text, WHITE)]
    a, b = text.split(keyword, 1)
    return [(a, WHITE), (keyword, ACCENT), (b, WHITE)]


def _text(layer: ImageDraw.ImageDraw, shadow: ImageDraw.ImageDraw, cx, y, runs, size, weight=800, alpha=1.0,
          anchor_left=None, max_w=900):
    f = font(size, weight)
    widths = [f.getlength(t) for t, _ in runs]
    while sum(widths) > max_w and size > 24:                 # shrink long lines to stay inside the safe area
        size -= 2
        f = font(size, weight)
        widths = [f.getlength(t) for t, _ in runs]
    x = anchor_left if anchor_left is not None else cx - sum(widths) / 2
    a = int(255 * alpha)
    for (t, col), w in zip(runs, widths):
        shadow.text((x + 3, y + 4), t, font=f, fill=(0, 0, 0, int(a * 0.85)), anchor="lm")
        layer.text((x, y), t, font=f, fill=col + (a,), anchor="lm")
        x += w


def clock_text(hud: dict, t: float, dur: float) -> str:
    c = hud.get("clock")
    if not c:
        return ""
    if "countdown" in c:                                   # 「夜が来るまで 2.73秒」
        left = max(0.0, c["countdown"] - t)
        return f"{left:0.2f}秒"
    q = min(1.0, t / max(dur, 0.01))
    minutes = c["from_min"] + (c["to_min"] - c["from_min"]) * q
    d, rem = divmod(int(minutes), 1440)
    hh, mm = divmod(rem, 60)
    return f"{d}日 {hh:02d}:{mm:02d}"


@lru_cache(maxsize=4)
def _scrim(kind: str) -> Image.Image:
    """Soft dark gradients so white text stays readable on bright 3D frames."""
    g = Image.new("L", (1, H), 0)
    for y in range(H):
        if kind == "top":
            a = 150 * max(0.0, 1 - y / 760) ** 1.4
        else:
            a = 140 * max(0.0, 1 - abs(y - 1190) / 230) ** 1.2
        g.putpixel((0, y), int(a))
    return Image.merge("RGBA", (Image.new("L", (W, H), 10), Image.new("L", (W, H), 14), Image.new("L", (W, H), 12),
                                g.resize((W, H))))


def _scrims(img, hud, t):
    out = Image.alpha_composite(img.convert("RGBA"), _scrim("top"))
    if hud.get("headline") and t >= hud.get("at", 0.6):
        k = ease((t - hud.get("at", 0.6)) / 0.45)
        mid = _scrim("mid")
        if k < 1:
            mid = mid.copy()
            mid.putalpha(mid.getchannel("A").point(lambda v: int(v * k)))
        out = Image.alpha_composite(out, mid)
    return out


def draw(img: Image.Image, t: float, dur: float, hud: dict, series: dict) -> Image.Image:
    """Return img (1080x1920 RGB) with the HUD for scene time t."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dl, ds = ImageDraw.Draw(layer), ImageDraw.Draw(shadow)
    img = _scrims(img, hud, t)
    # series question
    big_title = hud.get("big_title", False)
    q = series.get("question", "")
    if big_title:
        _text(dl, ds, W / 2 - 40, 520, _runs(q, series.get("keyword")), 70, 900)
    else:
        _text(dl, ds, W / 2 - 40, 268, _runs(q, series.get("keyword")), 46, 900)
    # clock block
    c = hud.get("clock")
    if c:
        x0 = 108
        y_label = 600 if big_title else 336
        label = c.get("label", "")
        speed = c.get("speed")
        _text(dl, ds, 0, y_label, [(label + (f"  ▶▶×{speed}" if speed else ""), MUTED)], 34, 800, anchor_left=x0)
        _text(dl, ds, 0, y_label + 58, [(clock_text(hud, t, dur), WHITE)], 70 if big_title else 64, 900, anchor_left=x0)
        dl.rectangle([x0, y_label + 104, x0 + 320, y_label + 110], fill=GREEN + (255,))
    if hud.get("place"):
        _text(dl, ds, 0, (760 if big_title else 476), [(hud["place"], MUTED)], 34, 800, anchor_left=108)
    # headline + sub (appear after `at` seconds)
    at = hud.get("at", 0.6)
    p = ease((t - at) / 0.45)
    if hud.get("headline") and p > 0:
        rise = (1 - p) * 24
        _text(dl, ds, W / 2 - 40, 1130 + rise, _runs(hud["headline"], hud.get("keyword")), 70, 900, alpha=p)
        for i, line in enumerate(hud.get("sub", [])):
            _text(dl, ds, W / 2 - 40, 1214 + i * 52 + rise, [(line, WHITE)], 38, 800, alpha=p)
    if hud.get("end_card") and t >= hud.get("end_at", 2.0):
        pe = ease((t - hud.get("end_at", 2.0)) / 0.5)
        box = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(box)
        bd.rounded_rectangle([100, 820, 940, 1080], radius=36, fill=(247, 243, 233, int(235 * pe)))
        layer = Image.alpha_composite(box, layer)
        dl = ImageDraw.Draw(layer)
        s1 = 56
        while font(s1, 900).getlength(hud["end_card"][0]) > 760 and s1 > 30:
            s1 -= 2
        f1, f2 = font(s1, 900), font(38, 700)
        dl.text((520, 900), hud["end_card"][0], font=f1, fill=(36, 48, 42, int(255 * pe)), anchor="mm")
        dl.text((520, 990), hud["end_card"][1], font=f2, fill=(47, 133, 90, int(255 * pe)), anchor="mm")
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    out = Image.alpha_composite(img.convert("RGBA"), shadow)
    out = Image.alpha_composite(out, layer)
    return out.convert("RGB")


def apply(frames_dir: Path, out_dir: Path, fps: int, hud: dict, series: dict):
    """Upscale each rendered frame to 1080x1920 and draw the HUD."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(frames_dir.glob("*.png"))
    dur = len(files) / fps
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGB")
        if im.size != (W, H):
            im = im.resize((W, H), Image.LANCZOS)
        draw(im, i / fps, dur, hud, series).save(out_dir / f"{i:04d}.png")
