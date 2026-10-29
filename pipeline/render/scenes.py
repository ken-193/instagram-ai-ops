"""Scene library. Each scene is draw(cv, t, dur, P, ctx) where
  t   : seconds since scene start
  dur : scene duration
  P   : scene["params"] from script.json
  ctx : SceneCtx (line timings, global time)

Scenes draw visuals + headline text only; subtitles are composited by the timeline.
Keep visuals inside y 220..1180 so the subtitle band (≈1230..1430) stays clear.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFilter

from .engine import (C, H, ROOT, SAFE, W, Canvas, clamp, ease_in_out, ease_out, ease_out_back, lerp, mix, seg,
                     shake, split_emphasis)


@dataclass
class SceneCtx:
    t_global: float
    lines: list[tuple[float, float]] = field(default_factory=list)  # narration line (start, end) in scene time

    def line_start(self, i: int, default: float = 0.0) -> float:
        return self.lines[i][0] if 0 <= i < len(self.lines) else default


SCENES: dict[str, callable] = {}


def scene(name):
    def deco(fn):
        SCENES[name] = fn
        return fn
    return deco


# ---------------------------------------------------------------- shared sprites
@lru_cache(maxsize=2)
def moon_sprite(px: int = 1000) -> Image.Image:
    rnd = random.Random(3)
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(60, 0, -1):  # shaded sphere
        f = i / 60
        r = px / 2 * f
        off = (1 - f) * px * 0.10
        c = int(lerp(120, 236, 1 - f * 0.85))
        d.ellipse([px / 2 - r - off, px / 2 - r - off, px / 2 + r - off, px / 2 + r - off], fill=(c, c, c - 4, 255))
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px - 1, px - 1], fill=255)
    craters = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    cd = ImageDraw.Draw(craters)
    for _ in range(55):
        r = rnd.uniform(px * 0.01, px * 0.07)
        x, y = rnd.uniform(0, px), rnd.uniform(0, px)
        cd.ellipse([x - r, y - r * 0.9, x + r, y + r * 0.9], fill=(70, 70, 75, rnd.randint(40, 95)))
        cd.ellipse([x - r * 0.8, y - r * 0.7, x + r * 0.7, y + r * 0.6], fill=(230, 230, 230, 25))
    for _ in range(7):  # maria
        r = rnd.uniform(px * 0.08, px * 0.18)
        x, y = rnd.uniform(px * 0.2, px * 0.8), rnd.uniform(px * 0.2, px * 0.8)
        cd.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=(60, 62, 70, 55))
    craters = craters.filter(ImageFilter.GaussianBlur(px / 400))
    img.alpha_composite(craters)
    img.putalpha(mask)
    return img


def draw_moon(cv: Canvas, x, y, r, glow=0.6):
    if r < 2:
        return
    if glow > 0:
        cv.glow(lambda d, k: d.ellipse([(x - r * 1.08) * k, (y - r * 1.08) * k, (x + r * 1.08) * k,
                                        (y + r * 1.08) * k], fill=(255, 255, 240, 200)), radius=r * 0.25 + 10,
                strength=glow)
    sp = moon_sprite().resize((max(2, int(2 * r * cv.ss)),) * 2, Image.LANCZOS)
    cv.img.alpha_composite(sp, (int((x - r) * cv.ss), int((y - r) * cv.ss)))


@lru_cache(maxsize=2)
def earth_sprite(px: int = 800) -> Image.Image:
    rnd = random.Random(11)
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(50, 0, -1):
        f = i / 50
        r = px / 2 * f
        off = (1 - f) * px * 0.08
        d.ellipse([px / 2 - r - off, px / 2 - r - off, px / 2 + r - off, px / 2 + r - off],
                  fill=mix((6, 30, 38), (14, 90, 92), 1 - f))
    land = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    ld = ImageDraw.Draw(land)
    for _ in range(26):
        cx, cy = rnd.uniform(px * 0.1, px * 0.9), rnd.uniform(px * 0.1, px * 0.9)
        pts = []
        n = 16
        base = rnd.uniform(px * 0.03, px * 0.09)
        for k in range(n):
            a = k / n * math.tau
            rr = base * rnd.uniform(0.6, 1.4)
            pts.append((cx + math.cos(a) * rr * 1.3, cy + math.sin(a) * rr))
        ld.polygon(pts, fill=C["emerald"] + (150,))
    land = land.filter(ImageFilter.GaussianBlur(px / 160))
    img.alpha_composite(land)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px - 1, px - 1], fill=255)
    img.putalpha(mask)
    ImageDraw.Draw(img).ellipse([2, 2, px - 3, px - 3], outline=C["emerald"] + (255,), width=max(2, px // 160))
    return img


def draw_earth(cv: Canvas, x, y, r):
    cv.glow(lambda d, k: d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=C["emerald"] + (160,)),
            radius=r * 0.2 + 8, strength=0.7)
    sp = earth_sprite().resize((max(2, int(2 * r * cv.ss)),) * 2, Image.LANCZOS)
    cv.img.alpha_composite(sp, (int((x - r) * cv.ss), int((y - r) * cv.ss)))


def headline(cv: Canvas, lines: list[str], emphasis: list[str], t: float, y0: float = 330, size: float = 84,
             gap: float = 1.25, delay: float = 0.0, stagger: float = 0.18, base=None):
    """Top-of-screen headline; each line pops in with ease_out_back."""
    base = base or C["white"]
    cx = (SAFE["left"] + W - SAFE["right"]) / 2
    for i, line in enumerate(lines):
        p = seg(t, delay + i * stagger, 0.45)
        if p <= 0:
            continue
        sc = 0.6 + 0.4 * ease_out_back(p)
        runs = split_emphasis(line, emphasis, base, C["yellow"])
        cv.rich_line(cx, y0 + i * size * gap, runs, size, stroke=4, alpha=clamp(p * 2), scale=sc)


def fmt_num(v: float, decimals: int = 0) -> str:
    return f"{v:,.{decimals}f}"


def counter_text(cv, x, y, value_from, value_to, p, unit="", prefix="", size=96, color=None, decimals=0,
                 unit_size=None):
    v = lerp(value_from, value_to, ease_out(p))
    s = prefix + fmt_num(v, decimals)
    color = color or C["yellow"]
    unit_size = unit_size or size * 0.55
    w, _ = cv.text_size(s, size)
    uw, _ = cv.text_size(unit, unit_size) if unit else (0, 0)
    left = x - (w + uw + 10) / 2
    cv.text(left, y, s, size, color, anchor="lm", stroke=4)
    if unit:
        cv.text(left + w + 10, y + size * 0.12, unit, unit_size, C["white"], anchor="lm", stroke=3)


# ---------------------------------------------------------------- scenes
@scene("moon_hook")
def moon_hook(cv: Canvas, t, dur, P, ctx: SceneCtx):
    p = ease_in_out(t / max(dur, 0.01))
    r = lerp(P.get("r_from", 150), P.get("r_to", 420), p)
    sx, sy = shake(t, 6 * seg(t, dur * 0.6, dur * 0.4))
    draw_moon(cv, 540 + sx, 860 + sy, r, glow=0.8)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=P.get("size", 92))


@scene("distance_compare")
def distance_compare(cv: Canvas, t, dur, P, ctx: SceneCtx):
    ex, ey, er = 210, 820, 120
    move_start = ctx.line_start(P.get("move_on_line", 1), 0.8)
    p = ease_in_out(seg(t, move_start, P.get("move_dur", 2.0)))
    d_from, d_to = 690, 345
    mx = ex + lerp(d_from, d_to, p)
    mr = lerp(46, 92, p)
    draw_earth(cv, ex, ey, er)
    # distance line
    y_line = ey + 230
    cv.line([(ex, y_line), (mx, y_line)], fill=C["white"] + (200,), width=4)
    for x in (ex, mx):
        cv.line([(x, y_line - 22), (x, y_line + 22)], fill=C["white"] + (230,), width=4)
    counter_text(cv, (ex + mx) / 2, y_line + 70, P["from_value"], P["to_value"], p, unit=P.get("unit", "km"),
                 size=70)
    draw_moon(cv, mx, ey, mr, glow=0.5)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=330, size=74)
    lab_p = seg(t, ctx.line_start(P.get("label_on_line", 2), dur * 0.7), 0.4)
    if lab_p > 0:
        sc = 0.6 + 0.4 * ease_out_back(lab_p)
        cv.rich_line(540, 560, split_emphasis(P.get("label", ""), P.get("emphasis_label", P.get("emphasis", [])), C["white"],
                                    C["yellow"]),
                     78, stroke=4, scale=sc, alpha=clamp(lab_p * 2))


@scene("formula_bars")
def formula_bars(cv: Canvas, t, dur, P, ctx: SceneCtx):
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    fp = seg(t, ctx.line_start(1, 0.6), 0.5)
    if fp > 0:
        cv.text(540, 470, P.get("formula", ""), 64, C["emerald"], family="sans", weight=900, stroke=3,
                alpha=clamp(fp * 2))
    base_y = 1120
    unit = 64
    grow = ease_out(seg(t, ctx.line_start(2, dur * 0.55), 1.0))
    bars = [(P.get("left_label", "今"), 1.0, C["gray"]), (P.get("right_label", "半分の距離"), lerp(1, P.get("ratio", 8), grow),
                                                         C["emerald"])]
    for i, (lab, val, col) in enumerate(bars):
        x = 330 + i * 360
        h = unit * val * (ease_out(seg(t, 0.2, 0.6)))
        cv.rect(x - 90, base_y - h, x + 90, base_y, fill=col + (255,), radius=12)
        cv.text(x, base_y + 50, lab, 44, C["white"], family="sans", weight=800)
        if i == 1 and grow > 0:
            cv.text(x, base_y - h - 70, f"×{val:.0f}" if grow >= 0.97 or val % 1 < 0.05 else f"×{val:.1f}", 110, C["yellow"], stroke=5)
    if grow >= 1:
        cv.glow(lambda d, k: d.rounded_rectangle([(690 - 90) * k, (base_y - unit * 8) * k, (690 + 90) * k,
                                                  base_y * k], radius=12 * k, fill=C["emerald"] + (255,)),
                radius=40, strength=0.5 + 0.3 * math.sin(t * 8))


@scene("globe_tides")
def globe_tides(cv: Canvas, t, dur, P, ctx: SceneCtx):
    cx, cy, r = 470, 760, 220
    amp = lerp(1.0, P.get("ratio", 8), ease_in_out(seg(t, 0.3, dur * 0.6)))
    bulge = 14 * amp
    ang = t * 0.25
    layer, d = cv.overlay()
    k = cv.ss
    pts = []
    for i in range(120):
        a = i / 120 * math.tau
        rr = r + 10 + bulge * (0.5 + 0.5 * math.cos(2 * (a - ang)))
        rr += 2.5 * math.sin(a * 9 + t * 6)
        pts.append(((cx + math.cos(a) * rr) * k, (cy + math.sin(a) * rr) * k))
    d.polygon(pts, fill=C["emerald"] + (110,), outline=C["emerald"] + (255,), width=int(3 * k))
    cv.img.alpha_composite(layer)
    draw_earth(cv, cx, cy, r)
    mx, my = cx + math.cos(ang) * 470, cy + math.sin(ang) * 470
    draw_moon(cv, mx, my, 60, glow=0.4)
    # ripple warnings around the globe
    for i in range(3):
        rp = ((t * 0.7 + i / 3) % 1.0)
        cv.circle(cx, cy, r + 40 + rp * 260, outline=C["yellow"] + (int(160 * (1 - rp)),), width=4)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    if P.get("note"):
        cv.text(540, 1160, P["note"], 34, C["gray"], family="sans", weight=600, alpha=clamp(t * 2))


# -- Japan map
@lru_cache(maxsize=1)
def japan():
    return json.loads((ROOT / "assets/geo/japan_prefectures.json").read_text(encoding="utf-8"))["prefectures"]


def proj(lon, lat, cam):
    clon, clat, scale = cam
    k = math.cos(math.radians(36))
    return (540 + (lon - clon) * scale * k, 700 - (lat - clat) * scale)


def draw_japan(cv: Canvas, cam, highlight=None, hl_color=None, hl_alpha=1.0, base_alpha=1.0, draw_p=1.0):
    k = cv.ss
    layer, d = cv.overlay()
    hl_layer, hd = cv.overlay()
    for pref in japan():
        is_hl = pref["iso"] == highlight
        for ring in pref["rings"]:
            n = len(ring) if draw_p >= 1 else max(2, int(len(ring) * draw_p))
            pts = [(x * k, y * k) for x, y in (proj(lo, la, cam) for lo, la in ring[:n])]
            if len(pts) < 3:
                continue
            if is_hl:
                hd.polygon(pts, fill=(hl_color or C["emerald"]) + (int(255 * hl_alpha),),
                           outline=C["white"] + (255,), width=int(3 * k))
            else:
                d.polygon(pts, fill=(28, 34, 38, int(255 * base_alpha)),
                          outline=C["emerald"] + (int(200 * base_alpha),), width=int(2 * k))
    cv.img.alpha_composite(layer)
    if highlight and hl_alpha > 0:
        glow = hl_layer.resize((hl_layer.width // 4, hl_layer.height // 4)).filter(ImageFilter.GaussianBlur(10))
        cv.img.alpha_composite(glow.resize(hl_layer.size))
        cv.img.alpha_composite(hl_layer)


def pin(cv: Canvas, x, y, label, p, color=None):
    if p <= 0:
        return
    color = color or C["yellow"]
    drop = (1 - ease_out_back(p)) * 60
    cv.circle(x, y - drop, 16, fill=color + (255,), outline=C["black"] + (255,), width=3)
    cv.circle(x, y, 26 + 30 * ((p * 2) % 1), outline=color + (int(200 * (1 - (p * 2) % 1)),), width=4)
    w, _ = cv.text_size(label, 50)
    cv.rect(x - w / 2 - 22, y - drop - 120, x + w / 2 + 22, y - drop - 44, fill=(0, 0, 0, 210),
            outline=color + (255,), width=3, radius=16)
    cv.text(x, y - drop - 82, label, 50, color)


JAPAN_CAM = (137.5, 37.0, 46.0)


@scene("japan_zoom")
def japan_zoom(cv: Canvas, t, dur, P, ctx: SceneCtx):
    tgt = P.get("target", {"lon": 134.4, "lat": 33.95, "scale": 380})
    zs = ctx.line_start(P.get("zoom_on_line", 1), dur * 0.4)
    zp = ease_in_out(seg(t, zs - 0.3, P.get("zoom_dur", 1.6)))
    # zoom in log-space for a natural feel
    scale = math.exp(lerp(math.log(JAPAN_CAM[2]), math.log(tgt["scale"]), zp))
    cam = (lerp(JAPAN_CAM[0], tgt["lon"], zp), lerp(JAPAN_CAM[1], tgt["lat"], zp), scale)
    hl_a = ease_out(seg(t, zs + 0.9, 0.5))
    draw_japan(cv, cam, highlight=P.get("highlight"), hl_alpha=hl_a, draw_p=ease_out(seg(t, 0, 0.9)))
    if P.get("pin"):
        pp = seg(t, zs + 1.2, 0.6)
        px, py = proj(P["pin"]["lon"], P["pin"]["lat"], cam)
        pin(cv, px, py, P["pin"]["label"], pp)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    if hl_a > 0 and P.get("big_label"):
        cv.text(540, 1080, P["big_label"], 120 * (0.7 + 0.3 * ease_out_back(hl_a)), C["yellow"], stroke=6,
                alpha=hl_a)


def draw_whirlpool(cv: Canvas, cx, cy, R, t, spin=1.0, alpha=1.0, arms=7):
    k = cv.ss
    layer, d = cv.overlay()
    for i in range(14, 0, -1):  # water body
        rr = R * i / 14
        col = mix((4, 40, 46), (12, 120, 110), i / 14)
        d.ellipse([(cx - rr) * k, (cy - rr * 0.92) * k, (cx + rr) * k, (cy + rr * 0.92) * k],
                  fill=col + (int(255 * alpha),))
    rot = t * spin
    for a_i in range(arms):
        base = a_i / arms * math.tau + rot
        pts = []
        for s in range(90):
            f = s / 89
            rr = R * (0.04 + 0.96 * f)
            a = base + f * 4.4
            pts.append(((cx + math.cos(a) * rr) * k, (cy + math.sin(a) * rr * 0.92) * k))
        for j in range(len(pts) - 1):
            f = j / len(pts)
            w = max(1, int((2 + 10 * f) * k))
            c = mix(C["white"], C["emerald"], f * 0.8)
            d.line([pts[j], pts[j + 1]], fill=c + (int(220 * alpha * (0.35 + 0.65 * f)),), width=w)
    d.ellipse([(cx - R * 0.07) * k, (cy - R * 0.06) * k, (cx + R * 0.07) * k, (cy + R * 0.06) * k],
              fill=(0, 0, 0, int(255 * alpha)))
    cv.img.alpha_composite(layer)


@scene("whirlpool")
def whirlpool(cv: Canvas, t, dur, P, ctx: SceneCtx):
    sp = ease_in_out(seg(t, ctx.line_start(1, dur * 0.35), 1.6))
    R = lerp(230, 360, sp)
    # integrate angle so speed changes don't jump
    ang = 1.6 * t + (5.0 - 1.6) * max(0.0, t - ctx.line_start(1, dur * 0.35)) * sp * 0.5
    sx, sy = shake(t, 5 * sp)
    draw_whirlpool(cv, 540 + sx, 760 + sy, R, ang)
    # speed counter
    c = P["speed"]
    cp = seg(t, ctx.line_start(1, dur * 0.35), 1.6)
    cv.text(540, 300, c.get("label", "潮流の速さ"), 46, C["white"], family="sans", weight=800, alpha=clamp(t * 3))
    counter_text(cv, 540, 390, c["from"], c["to"] if cp > 0 else c["from"], cp, unit=c.get("unit", "km/h"),
                 prefix=c.get("prefix", "時速"), size=100)
    ep = seg(t, ctx.line_start(2, dur * 0.7), 0.5)
    if ep > 0:
        e = P["energy"]
        cv.rect(170, 1080 - 70, 910, 1080 + 70, fill=(0, 0, 0, 200), outline=C["yellow"] + (255,), width=4, radius=20)
        cv.rich_line(540, 1080, split_emphasis(e["text"], e.get("emphasis", []), C["white"], C["yellow"]), 72,
                     stroke=4, scale=0.7 + 0.3 * ease_out_back(ep), alpha=clamp(ep * 2))


@scene("power_ochi")
def power_ochi(cv: Canvas, t, dur, P, ctx: SceneCtx):
    cam = (P.get("lon", 134.2), P.get("lat", 34.0), P.get("scale", 300))
    flare = ease_out(seg(t, ctx.line_start(1, dur * 0.3), 0.6))
    draw_japan(cv, cam, highlight=P.get("highlight", "JP-36"), hl_color=mix(C["emerald"], C["yellow"], flare * 0.5),
               hl_alpha=1.0, base_alpha=0.8)
    ox, oy = proj(134.35, 33.95, cam)
    rnd = random.Random(int(t * 12))
    if flare > 0:
        for i in range(10):
            a = i / 10 * math.tau + 0.3
            L = 600 * flare
            pts = [(ox, oy)]
            for s in range(1, 8):
                f = s / 7
                jitter = rnd.uniform(-22, 22)
                pts.append((ox + math.cos(a) * L * f - math.sin(a) * jitter, oy + math.sin(a) * L * f + math.cos(a) * jitter))
            cv.glow(lambda d, k, pts=pts: d.line([(x * k, y * k) for x, y in pts], fill=C["yellow"] + (255,),
                                                  width=int(10 * k)), radius=20, strength=0.9)
            cv.line(pts, fill=C["white"] + (255,), width=4)
    draw_whirlpool(cv, ox + 70, oy - 70, 70, t * 6, alpha=0.95, arms=5)
    lp = seg(t, ctx.line_start(2, dur * 0.6), 0.5)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=290, size=74)
    if lp > 0:
        sx, sy = shake(t, 4 * (1 - lp))
        cv.rect(110, 980, 970, 1170, fill=(0, 0, 0, 215), outline=C["emerald"] + (255,), width=5, radius=26)
        for i, l in enumerate(P.get("stamp", [])):
            cv.rich_line(540 + sx, 1030 + i * 90 + sy, split_emphasis(l, P.get("emphasis", []), C["white"], C["yellow"]),
                         70, stroke=4, scale=0.6 + 0.4 * ease_out_back(lp), alpha=clamp(lp * 2))


@scene("outro_question")
def outro_question(cv: Canvas, t, dur, P, ctx: SceneCtx):
    draw_whirlpool(cv, 540, 820, 330, t * 5, alpha=0.55)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=330, size=84)
    qp = seg(t, ctx.line_start(1, dur * 0.45), 0.45)
    if qp > 0:
        cv.rect(150, 960, 930, 1140, fill=C["emerald"] + (240,), radius=30)
        cv.text(540, 1050, P.get("question", ""), 70 * (0.7 + 0.3 * ease_out_back(qp)), C["black"], alpha=clamp(qp * 2))
    if P.get("footer"):
        cv.text(540, 1470, P["footer"], 38, C["emerald"], family="sans", weight=800, alpha=clamp(t * 2))
