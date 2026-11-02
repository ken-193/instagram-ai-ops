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
    craters = craters.convert("RGBa").filter(ImageFilter.GaussianBlur(px / 400)).convert("RGBA")
    img.alpha_composite(craters)
    img.putalpha(mask)
    return img


def draw_moon(cv: Canvas, x, y, r, glow=0.6):
    if r < 2:
        return
    if glow > 0:
        cv.glow(lambda d, k: d.ellipse([(x - r * 1.08) * k, (y - r * 1.08) * k, (x + r * 1.08) * k,
                                        (y + r * 1.08) * k], fill=C["paper"] + (255,)), radius=r * 0.25 + 10,
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
                  fill=mix(C["sub_light"], (232, 243, 236), 1 - f))
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
        ld.polygon(pts, fill=C["sub"] + (200,))
    land = land.convert("RGBa").filter(ImageFilter.GaussianBlur(px / 160)).convert("RGBA")
    img.alpha_composite(land)
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, px - 1, px - 1], fill=255)
    img.putalpha(mask)
    ImageDraw.Draw(img).ellipse([2, 2, px - 3, px - 3], outline=C["sub_dark"] + (255,), width=max(2, px // 160))
    return img


def draw_earth(cv: Canvas, x, y, r):
    cv.glow(lambda d, k: d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=C["sub_light"] + (200,)),
            radius=r * 0.2 + 8, strength=0.7)
    sp = earth_sprite().resize((max(2, int(2 * r * cv.ss)),) * 2, Image.LANCZOS)
    cv.img.alpha_composite(sp, (int((x - r) * cv.ss), int((y - r) * cv.ss)))


def headline(cv: Canvas, lines: list[str], emphasis: list[str], t: float, y0: float = 330, size: float = 84,
             gap: float = 1.25, delay: float = 0.0, stagger: float = 0.18, base=None):
    """Top-of-screen headline; each line pops in with ease_out_back."""
    base = base or C["ink"]
    cx = (SAFE["left"] + W - SAFE["right"]) / 2
    for i, line in enumerate(lines):
        p = seg(t, delay + i * stagger, 0.45)
        if p <= 0:
            continue
        sc = 0.6 + 0.4 * ease_out_back(p)
        runs = split_emphasis(line, emphasis, base, C["accent"])
        cv.rich_line(cx, y0 + i * size * gap, runs, size, stroke=4, alpha=clamp(p * 2), scale=sc)


def fmt_num(v: float, decimals: int = 0) -> str:
    return f"{v:,.{decimals}f}"


def counter_text(cv, x, y, value_from, value_to, p, unit="", prefix="", size=96, color=None, decimals=0,
                 unit_size=None):
    v = lerp(value_from, value_to, ease_out(p))
    s = prefix + fmt_num(v, decimals)
    color = color or C["accent"]
    unit_size = unit_size or size * 0.55
    w, _ = cv.text_size(s, size)
    uw, _ = cv.text_size(unit, unit_size) if unit else (0, 0)
    left = x - (w + uw + 10) / 2
    cv.text(left, y, s, size, color, anchor="lm", stroke=4)
    if unit:
        cv.text(left + w + 10, y + size * 0.12, unit, unit_size, C["ink"], anchor="lm", stroke=3)


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
    cv.line([(ex, y_line), (mx, y_line)], fill=C["ink"] + (200,), width=4)
    for x in (ex, mx):
        cv.line([(x, y_line - 22), (x, y_line + 22)], fill=C["ink"] + (230,), width=4)
    counter_text(cv, (ex + mx) / 2, y_line + 70, P["from_value"], P["to_value"], p, unit=P.get("unit", "km"),
                 size=70)
    draw_moon(cv, mx, ey, mr, glow=0.5)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=330, size=74)
    lab_p = seg(t, ctx.line_start(P.get("label_on_line", 2), dur * 0.7), 0.4)
    if lab_p > 0:
        sc = 0.6 + 0.4 * ease_out_back(lab_p)
        cv.rich_line(540, 560, split_emphasis(P.get("label", ""), P.get("emphasis_label", P.get("emphasis", [])), C["ink"],
                                    C["accent"]),
                     78, stroke=4, scale=sc, alpha=clamp(lab_p * 2))


@scene("formula_bars")
def formula_bars(cv: Canvas, t, dur, P, ctx: SceneCtx):
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    fp = seg(t, ctx.line_start(1, 0.6), 0.5)
    if fp > 0:
        cv.text(540, 470, P.get("formula", ""), 64, C["sub"], family="sans", weight=900, stroke=3,
                alpha=clamp(fp * 2))
    base_y = 1120
    unit = 64
    grow = ease_out(seg(t, ctx.line_start(2, dur * 0.55), 1.0))
    bars = [(P.get("left_label", "今"), 1.0, C["muted"]), (P.get("right_label", "半分の距離"), lerp(1, P.get("ratio", 8), grow),
                                                         C["sub"])]
    for i, (lab, val, col) in enumerate(bars):
        x = 330 + i * 360
        h = unit * val * (ease_out(seg(t, 0.2, 0.6)))
        cv.rect(x - 90, base_y - h, x + 90, base_y, fill=col + (255,), radius=12)
        cv.text(x, base_y + 50, lab, 44, C["ink"], family="sans", weight=800)
        if i == 1 and grow > 0:
            cv.text(x, base_y - h - 70, f"×{val:.0f}" if grow >= 0.97 or val % 1 < 0.05 else f"×{val:.1f}", 110, C["accent"], stroke=5)
    if grow >= 1:
        cv.glow(lambda d, k: d.rounded_rectangle([(690 - 90) * k, (base_y - unit * 8) * k, (690 + 90) * k,
                                                  base_y * k], radius=12 * k, fill=C["sub"] + (255,)),
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
    d.polygon(pts, fill=C["sub"] + (110,), outline=C["sub"] + (255,), width=int(3 * k))
    cv.img.alpha_composite(layer)
    draw_earth(cv, cx, cy, r)
    mx, my = cx + math.cos(ang) * 470, cy + math.sin(ang) * 470
    draw_moon(cv, mx, my, 60, glow=0.4)
    # ripple warnings around the globe
    for i in range(3):
        rp = ((t * 0.7 + i / 3) % 1.0)
        cv.circle(cx, cy, r + 40 + rp * 260, outline=C["accent"] + (int(160 * (1 - rp)),), width=4)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    if P.get("note"):
        cv.text(540, 1160, P["note"], 34, C["muted"], family="sans", weight=600, alpha=clamp(t * 2))


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
                hd.polygon(pts, fill=(hl_color or C["sub"]) + (int(255 * hl_alpha),),
                           outline=C["paper"] + (255,), width=int(3 * k))
            else:
                d.polygon(pts, fill=C["land"] + (int(255 * base_alpha),),
                          outline=C["sub"] + (int(170 * base_alpha),), width=int(2 * k))
    cv.img.alpha_composite(layer)
    if highlight and hl_alpha > 0:
        glow = hl_layer.resize((hl_layer.width // 4, hl_layer.height // 4)).convert("RGBa").filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
        cv.img.alpha_composite(glow.resize(hl_layer.size))
        cv.img.alpha_composite(hl_layer)


def pin(cv: Canvas, x, y, label, p, color=None):
    if p <= 0:
        return
    color = color or C["accent"]
    drop = (1 - ease_out_back(p)) * 60
    cv.circle(x, y - drop, 16, fill=color + (255,), outline=C["paper"] + (255,), width=3)
    cv.circle(x, y, 26 + 30 * ((p * 2) % 1), outline=color + (int(200 * (1 - (p * 2) % 1)),), width=4)
    w, _ = cv.text_size(label, 50)
    cv.rect(x - w / 2 - 22, y - drop - 120, x + w / 2 + 22, y - drop - 44, fill=C["paper"] + (240,),
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
        cv.text(540, 1080, P["big_label"], 120 * (0.7 + 0.3 * ease_out_back(hl_a)), C["accent"], stroke=6,
                alpha=hl_a)


def draw_whirlpool(cv: Canvas, cx, cy, R, t, spin=1.0, alpha=1.0, arms=7):
    k = cv.ss
    layer, d = cv.overlay()
    for i in range(14, 0, -1):  # water body
        rr = R * i / 14
        col = mix(C["sub_dark"], C["sub"], i / 14)
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
            c = mix(C["paper"], C["sub_light"], f * 0.8)
            d.line([pts[j], pts[j + 1]], fill=c + (int(220 * alpha * (0.35 + 0.65 * f)),), width=w)
    d.ellipse([(cx - R * 0.07) * k, (cy - R * 0.06) * k, (cx + R * 0.07) * k, (cy + R * 0.06) * k],
              fill=C["ink"] + (int(255 * alpha),))
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
    cv.text(540, 300, c.get("label", "潮流の速さ"), 46, C["ink"], family="sans", weight=800, alpha=clamp(t * 3))
    counter_text(cv, 540, 390, c["from"], c["to"] if cp > 0 else c["from"], cp, unit=c.get("unit", "km/h"),
                 prefix=c.get("prefix", "時速"), size=100)
    ep = seg(t, ctx.line_start(2, dur * 0.7), 0.5)
    if ep > 0:
        e = P["energy"]
        cv.rect(170, 1080 - 70, 910, 1080 + 70, fill=C["paper"] + (245,), outline=C["accent"] + (255,), width=4, radius=20)
        cv.rich_line(540, 1080, split_emphasis(e["text"], e.get("emphasis", []), C["ink"], C["accent"]), 72,
                     stroke=4, scale=0.7 + 0.3 * ease_out_back(ep), alpha=clamp(ep * 2))


@scene("power_ochi")
def power_ochi(cv: Canvas, t, dur, P, ctx: SceneCtx):
    cam = (P.get("lon", 134.2), P.get("lat", 34.0), P.get("scale", 300))
    flare = ease_out(seg(t, ctx.line_start(1, dur * 0.3), 0.6))
    draw_japan(cv, cam, highlight=P.get("highlight", "JP-36"), hl_color=C["sub"],
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
            cv.glow(lambda d, k, pts=pts: d.line([(x * k, y * k) for x, y in pts], fill=C["accent"] + (255,),
                                                  width=int(10 * k)), radius=20, strength=0.9)
            cv.line(pts, fill=C["paper"] + (255,), width=4)
    draw_whirlpool(cv, ox + 70, oy - 70, 70, t * 6, alpha=0.95, arms=5)
    lp = seg(t, ctx.line_start(2, dur * 0.6), 0.5)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=290, size=74)
    if lp > 0:
        sx, sy = shake(t, 4 * (1 - lp))
        cv.rect(110, 980, 970, 1170, fill=C["paper"] + (245,), outline=C["sub"] + (255,), width=5, radius=26)
        for i, l in enumerate(P.get("stamp", [])):
            cv.rich_line(540 + sx, 1030 + i * 90 + sy, split_emphasis(l, P.get("emphasis", []), C["ink"], C["accent"]),
                         70, stroke=4, scale=0.6 + 0.4 * ease_out_back(lp), alpha=clamp(lp * 2))


@scene("outro_question")
def outro_question(cv: Canvas, t, dur, P, ctx: SceneCtx):
    bg = P.get("bg", "whirlpool")
    if bg == "whirlpool":
        draw_whirlpool(cv, 540, 820, 330, t * 5, alpha=0.55)
    elif bg == "dance":
        draw_dancers(cv, t, rows=4, cols=7, top=560, bottom=900, alpha=0.5)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=330, size=84)
    qp = seg(t, ctx.line_start(1, dur * 0.45), 0.45)
    if qp > 0:
        cv.rect(150, 960, 930, 1140, fill=C["sub"] + (250,), radius=30)
        cv.text(540, 1050, P.get("question", ""), 70 * (0.7 + 0.3 * ease_out_back(qp)), C["paper"], alpha=clamp(qp * 2), stroke_fill=C["sub"])
    if P.get("footer"):
        cv.text(540, 1470, P["footer"], 38, C["sub"], family="sans", weight=800, alpha=clamp(t * 2))


# ---------------------------------------------------------------- people / crowds
def draw_person(cv: Canvas, x, y, s, color, pose=0.0, dance=False):
    """Simple pictogram person standing at (x, y = feet). s = height in px.
    dance=True raises both arms (Awa-odori style); pose (radians) swings them."""
    k = cv.ss
    head_r = s * 0.11
    neck = (x, y - s * 0.74)
    hip = (x, y - s * 0.36)
    cv.circle(x, y - s * 0.86, head_r, fill=color + (255,))
    w = max(2, s * 0.09)
    cv.line([neck, hip], fill=color + (255,), width=w)
    sw = math.sin(pose)
    cv.line([hip, (x - s * 0.16 - sw * s * 0.04, y)], fill=color + (255,), width=w)
    cv.line([hip, (x + s * 0.16 - sw * s * 0.04, y)], fill=color + (255,), width=w)
    shoulder = (x, y - s * 0.68)
    if dance:
        for side in (-1, 1):
            elbow = (x + side * s * 0.2, y - s * (0.84 + 0.06 * sw * side))
            hand = (x + side * s * (0.16 + 0.08 * sw), y - s * (1.06 + 0.05 * sw * side))
            cv.line([shoulder, elbow, hand], fill=color + (255,), width=w * 0.85)
    else:
        for side in (-1, 1):
            cv.line([shoulder, (x + side * s * 0.17, y - s * 0.42)], fill=color + (255,), width=w * 0.85)


def draw_dancers(cv: Canvas, t, rows=5, cols=7, top=520, bottom=1150, alpha=1.0, accent_every=5):
    """Rows of Awa-odori dancers in loose perspective (smaller and paler at the back)."""
    for r in range(rows):
        f = r / max(1, rows - 1)                       # 0 = back row, 1 = front row
        y = lerp(top, bottom, f)
        size = lerp(70, 150, f)
        n = cols + (rows - 1 - r)
        for c in range(n):
            x = 120 + (840 / max(1, n - 1)) * c + (r % 2) * 18
            phase = t * 6.5 + c * 0.9 + r * 1.3
            bob = abs(math.sin(phase)) * size * 0.06
            base = C["accent"] if (r * 7 + c) % accent_every == 0 else C["sub"] if (r + c) % 3 == 0 else C["ink"]
            col = mix(C["bg"], base, (0.35 + 0.65 * f) * alpha)
            draw_person(cv, x, y - bob, size, col, pose=phase, dance=True)


@lru_cache(maxsize=4)
def pref_points(iso: str, n: int, seed: int = 5):
    """n random lon/lat points inside a prefecture (rejection sampling on its polygons)."""
    rings = next(p["rings"] for p in japan() if p["iso"] == iso)
    lons = [x for r in rings for x, _ in r]
    lats = [y for r in rings for _, y in r]

    def inside(px, py):
        hit = False
        for ring in rings:
            j = len(ring) - 1
            for i in range(len(ring)):
                xi, yi = ring[i]
                xj, yj = ring[j]
                if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-12) + xi:
                    hit = not hit
                j = i
        return hit

    rnd = random.Random(seed)
    pts = []
    while len(pts) < n:
        x, y = rnd.uniform(min(lons), max(lons)), rnd.uniform(min(lats), max(lats))
        if inside(x, y):
            pts.append((x, y, rnd.random()))
    return pts


@scene("crowd_hook")
def crowd_hook(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """People from all over the globe stream into one glowing point (Tokushima)."""
    cx, cy, r = 540, 800, 250
    draw_earth(cv, cx, cy, r)
    tx, ty = cx + r * 0.42, cy - r * 0.18
    rnd = random.Random(9)
    k = cv.ss
    layer, d = cv.overlay()
    for i in range(220):
        a, rr = rnd.uniform(0, math.tau), r * math.sqrt(rnd.random()) * 0.95
        sx, sy = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        start = rnd.uniform(0, dur * 0.55)
        p = ease_in_out(seg(t, start, dur * 0.4))
        bend = math.sin(p * math.pi) * 60 * (1 if i % 2 else -1)
        x = lerp(sx, tx, p) + bend * 0.3
        y = lerp(sy, ty, p) - bend
        col = C["accent"] if i % 6 == 0 else C["ink"]
        rad = 5.5 * (1 - 0.6 * p)
        d.ellipse([(x - rad) * k, (y - rad) * k, (x + rad) * k, (y + rad) * k], fill=col + (235,))
    cv.img.alpha_composite(layer)
    pulse = 0.5 + 0.5 * math.sin(t * 7)
    gather = seg(t, dur * 0.3, dur * 0.6)
    cv.glow(lambda dd, kk: dd.ellipse([(tx - 30) * kk, (ty - 30) * kk, (tx + 30) * kk, (ty + 30) * kk],
                                        fill=C["accent"] + (255,)), radius=30, strength=0.4 + 0.6 * gather * pulse)
    cv.circle(tx, ty, 12 + 10 * gather, fill=C["accent"] + (255,), outline=C["paper"] + (255,), width=3)
    if P.get("pin_label"):
        cv.text(tx, ty - 60, P["pin_label"], 46, C["accent"], alpha=gather, stroke=4)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=P.get("size", 84))


@scene("big_counter")
def big_counter(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Label + big number counting up, a growing grid of people icons, then a multiplier stamp."""
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    cp = seg(t, ctx.line_start(P.get("count_on_line", 0), 0.3), P.get("count_dur", 1.4))
    counter_text(cv, 540, 470, P["from"], P["to"] if cp > 0 else P["from"], cp, unit=P.get("unit", ""),
                 prefix=P.get("prefix", ""), size=P.get("size", 110))
    grow = ease_out(seg(t, ctx.line_start(P.get("grid_on_line", 1), dur * 0.4), 1.6))
    cols, rows = 12, 9
    shown = int(1 + grow * (cols * rows - 1))
    for i in range(shown):
        c, rr = i % cols, i // cols
        x, y = 150 + c * 70, 620 + rr * 62
        col = C["accent"] if i == 0 else C["sub"] if i % 7 == 0 else C["ink"]
        draw_person(cv, x, y + 50, 52, mix(C["bg"], col, 0.9))
    mp = seg(t, ctx.line_start(P.get("stamp_on_line", 1), dur * 0.6), 0.5)
    if mp > 0 and P.get("stamp"):
        sc = 0.6 + 0.4 * ease_out_back(mp)
        cv.rect(170, 1050, 910, 1180, fill=C["paper"] + (245,), outline=C["accent"] + (255,), width=5, radius=24)
        cv.rich_line(540, 1115, split_emphasis(P["stamp"], P.get("stamp_emphasis", []), C["ink"], C["accent"]), 76,
                     stroke=0, scale=sc, alpha=clamp(mp * 2))


@scene("tatami")
def tatami(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Top view of one tatami mat that fills up with people (heads + shoulders)."""
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=70)
    x0, y0, w, h = 330, 470, 420, 680           # ~1:1.6 like a real mat, vertical
    cv.rect(x0, y0, x0 + w, y0 + h, fill=(214, 201, 150, 255), outline=C["sub_dark"] + (255,), width=14, radius=6)
    for i in range(1, 22):                       # woven texture
        yy = y0 + h * i / 22
        cv.line([(x0 + 12, yy), (x0 + w - 12, yy)], fill=(190, 176, 122, 255), width=2)
    n = P.get("people", 3)
    seats = P.get("seats", [(0.5, 0.2), (0.28, 0.62), (0.72, 0.62), (0.5, 0.92)])
    for i in range(n):
        pp = ease_out_back(seg(t, ctx.line_start(P.get("fill_on_line", 1), 0.4) + i * 0.35, 0.4))
        if pp <= 0:
            continue
        fx, fy = seats[i % len(seats)]
        x, y = x0 + w * fx, y0 + h * fy - 60
        sc = 0.4 + 0.6 * pp
        col = C["accent"] if i == 0 else C["ink"]
        cv.circle(x, y + 38 * sc, 92 * sc, fill=mix(C["bg"], col, 0.55) + (230,))   # shoulders
        cv.circle(x, y, 48 * sc, fill=col + (255,))                                     # head
    lp = seg(t, ctx.line_start(P.get("label_on_line", 1), dur * 0.6), 0.4)
    if lp > 0 and P.get("label"):
        cv.rect(150, 1160 - 66, 930, 1160 + 66, fill=C["paper"] + (245,), outline=C["accent"] + (255,), width=5, radius=22)
        cv.rich_line(540, 1160, split_emphasis(P["label"], P.get("label_emphasis", []), C["ink"], C["accent"]), 68,
                     stroke=0, scale=0.7 + 0.3 * ease_out_back(lp), alpha=clamp(lp * 2))


@scene("crowd_map")
def crowd_map(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Zoomed prefecture map that fills with a jittering crowd."""
    iso = P.get("iso", "JP-36")
    cam = (P.get("lon", 134.3), P.get("lat", 33.95), P.get("scale", 360))
    draw_japan(cv, cam, highlight=iso, hl_color=C["sub_light"], hl_alpha=1.0, base_alpha=0.9)
    fill = ease_in_out(seg(t, ctx.line_start(P.get("fill_on_line", 0), 0.2), dur * 0.75))
    pts = pref_points(iso, 1400)
    k = cv.ss
    layer, d = cv.overlay()
    for i, (lo, la, rnd) in enumerate(pts):
        if rnd > fill:
            continue
        x, y = proj(lo, la, cam)
        x += math.sin(t * 9 + i) * 1.6
        y += math.cos(t * 7 + i * 1.7) * 1.6
        col = C["accent"] if i % 9 == 0 else C["ink"] if i % 2 else C["sub_dark"]
        d.ellipse([(x - 4) * k, (y - 4) * k, (x + 4) * k, (y + 4) * k], fill=col + (240,))
    cv.img.alpha_composite(layer)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=290, size=74)
    for j, tag in enumerate(P.get("tags", [])):
        tp = seg(t, ctx.line_start(tag.get("on_line", 1), dur * 0.5) + j * 0.25, 0.4)
        if tp <= 0:
            continue
        x, y = proj(tag["lon"], tag["lat"], cam)
        w, _ = cv.text_size(tag["text"], 40)
        cv.rect(x - w / 2 - 18, y - 34, x + w / 2 + 18, y + 34, fill=C["paper"] + (240,), outline=C["sub"] + (255,),
                width=3, radius=14)
        cv.text(x, y, tag["text"], 40 * (0.7 + 0.3 * ease_out_back(tp)), C["ink"], alpha=clamp(tp * 2))


@scene("world_empty")
def world_empty(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Globe dotted with people who vanish everywhere except one hot spot; '0人' tags pop up."""
    cx, cy, r = 540, 800, 260
    draw_earth(cv, cx, cy, r)
    hx, hy = cx + r * 0.42, cy - r * 0.18
    fade = ease_in_out(seg(t, ctx.line_start(P.get("fade_on_line", 0), 0.2), dur * 0.5))
    rnd = random.Random(13)
    k = cv.ss
    layer, d = cv.overlay()
    for i in range(260):
        a, rr = rnd.uniform(0, math.tau), r * math.sqrt(rnd.random()) * 0.93
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        vanish = rnd.uniform(0, 1)
        if vanish < fade:
            continue
        d.ellipse([(x - 4) * k, (y - 4) * k, (x + 4) * k, (y + 4) * k], fill=C["ink"] + (220,))
    cv.img.alpha_composite(layer)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    cv.glow(lambda dd, kk: dd.ellipse([(hx - 34) * kk, (hy - 34) * kk, (hx + 34) * kk, (hy + 34) * kk],
                                        fill=C["accent"] + (255,)), radius=34, strength=0.5 + 0.5 * pulse)
    cv.circle(hx, hy, 18, fill=C["accent"] + (255,), outline=C["paper"] + (255,), width=3)
    for j, tag in enumerate(P.get("tags", [])):
        tp = seg(t, ctx.line_start(tag.get("on_line", 1), dur * 0.5) + j * 0.3, 0.4)
        if tp <= 0:
            continue
        x, y = tag["x"], tag["y"]
        w, _ = cv.text_size(tag["text"], 44)
        cv.rect(x - w / 2 - 20, y - 38, x + w / 2 + 20, y + 38, fill=C["paper"] + (245,), outline=C["ink"] + (255,),
                width=3, radius=16)
        cv.rich_line(x, y, split_emphasis(tag["text"], ["0人"], C["ink"], C["accent"]), 44,
                     scale=0.7 + 0.3 * ease_out_back(tp), alpha=clamp(tp * 2))
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=74)


@scene("dance_crowd")
def dance_crowd(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Everyone dancing (Awa-odori). Optional counter and stamp panel."""
    draw_dancers(cv, t, rows=P.get("rows", 5), cols=P.get("cols", 7), top=560, bottom=1180)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=76)
    if P.get("stamp"):
        sp = seg(t, ctx.line_start(P.get("stamp_on_line", 1), dur * 0.5), 0.5)
        if sp > 0:
            sx, sy = shake(t, 3 * (1 - sp))
            cv.rect(130, 470, 950, 600, fill=C["paper"] + (245,), outline=C["accent"] + (255,), width=5, radius=24)
            cv.rich_line(540 + sx, 535 + sy, split_emphasis(P["stamp"], P.get("stamp_emphasis", []), C["ink"],
                                                            C["accent"]),
                         66, scale=0.6 + 0.4 * ease_out_back(sp), alpha=clamp(sp * 2))


# ---------------------------------------------------------------- space trip
def draw_rocket(cv: Canvas, x, y, angle, size=60):
    """Small rocket pointing along `angle` (radians, 0 = right)."""
    ca, sa = math.cos(angle), math.sin(angle)

    def P(u, v):  # u along the rocket, v across
        return (x + ca * u * size - sa * v * size, y + sa * u * size + ca * v * size)

    flame = 0.25 + 0.1 * math.sin(cv.ss * 1000 + x)
    cv.polygon([P(-0.55, -0.12), P(-0.55 - flame - 0.3, 0), P(-0.55, 0.12)], fill=C["accent"] + (230,))
    cv.polygon([P(-0.45, -0.18), P(-0.75, -0.38), P(-0.3, -0.18)], fill=C["accent"] + (255,))
    cv.polygon([P(-0.45, 0.18), P(-0.75, 0.38), P(-0.3, 0.18)], fill=C["accent"] + (255,))
    cv.polygon([P(-0.55, -0.2), P(0.3, -0.2), P(0.7, 0), P(0.3, 0.2), P(-0.55, 0.2)], fill=C["paper"] + (255,),
               outline=C["ink"] + (255,), width=3)
    wx, wy = P(0.15, 0)
    cv.circle(wx, wy, size * 0.09, fill=C["sub"] + (255,), outline=C["ink"] + (255,), width=2)


def draw_galaxy(cv: Canvas, cx, cy, R, t):
    rnd = random.Random(21)
    k = cv.ss
    layer, d = cv.overlay()
    for i in range(900):
        arm = i % 2
        f = rnd.random() ** 0.7
        a = arm * math.pi + f * 4.2 + t * 0.15 + rnd.gauss(0, 0.25)
        rr = R * f
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.55
        col = C["sub"] if f > 0.3 else C["accent"]
        s = 1.6 + 2.2 * (1 - f)
        d.ellipse([(x - s) * k, (y - s) * k, (x + s) * k, (y + s) * k], fill=col + (int(110 + 120 * (1 - f)),))
    cv.img.alpha_composite(layer)
    cv.glow(lambda dd, kk: dd.ellipse([(cx - R * 0.18) * kk, (cy - R * 0.1) * kk, (cx + R * 0.18) * kk,
                                         (cy + R * 0.1) * kk], fill=C["accent"] + (255,)), radius=R * 0.15, strength=0.6)


def draw_cosmic_web(cv: Canvas, cx, cy, R, t):
    rnd = random.Random(33)
    k = cv.ss
    pts = [(cx + R * math.sqrt(rnd.random()) * math.cos(a), cy + R * math.sqrt(rnd.random()) * math.sin(a))
           for a in (rnd.uniform(0, math.tau) for _ in range(140))]
    layer, d = cv.overlay()
    for i, (x, y) in enumerate(pts):
        for (x2, y2) in pts[i + 1:i + 4]:
            if (x - x2) ** 2 + (y - y2) ** 2 < (R * 0.28) ** 2:
                d.line([(x * k, y * k), (x2 * k, y2 * k)], fill=C["sub"] + (90,), width=int(2 * k))
        s = 3 + 3 * (0.5 + 0.5 * math.sin(t * 3 + i))
        d.ellipse([(x - s) * k, (y - s) * k, (x + s) * k, (y + s) * k], fill=C["ink"] + (200,))
    cv.img.alpha_composite(layer)
    cv.circle(cx, cy, R + 14, outline=C["accent"] + (220,), width=5)


@scene("rocket_launch")
def rocket_launch(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Big Earth at the bottom; a rocket lifts off from an UNLABELLED dot (the reveal comes later)."""
    ex, ey, er = 540, 1560, 640
    draw_earth(cv, ex, ey, er)
    sx, sy = ex + er * 0.22, ey - er * 0.975          # launch site on the rim (deliberately unnamed)
    cv.circle(sx, sy, 9, fill=C["accent"] + (255,), outline=C["paper"] + (255,), width=3)
    p = ease_in_out(seg(t, 0.4, dur * 0.85))
    rx, ry = lerp(sx, 800, p), lerp(sy, 640, p)
    for j in range(14):                               # exhaust trail
        q = max(0.0, p - j * 0.02)
        tx, ty = lerp(sx, 800, q), lerp(sy, 640, q)
        cv.circle(tx, ty, 10 + j * 1.5, fill=C["line"] + (int(200 * (1 - j / 14) * min(1, p * 4)),))
    draw_rocket(cv, rx, ry, math.atan2(640 - sy, 800 - sx), 110)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=P.get("size", 86))


@scene("cosmic_jump")
def cosmic_jump(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """One stop of a zoom-out trip: destination object + distance + light-travel time; rocket cruising."""
    obj = P.get("object", "moon")
    cx, cy = 540, 760
    app = ease_out(seg(t, 0, 0.8))
    if obj == "moon":
        draw_moon(cv, cx, cy, 240 * app, glow=0.4)
    elif obj == "sun":
        R = 220 * app
        cv.glow(lambda d, k: d.ellipse([(cx - R * 1.1) * k, (cy - R * 1.1) * k, (cx + R * 1.1) * k, (cy + R * 1.1) * k],
                                        fill=C["accent"] + (255,)), radius=R * 0.35 + 10, strength=0.6)
        for i in range(16):
            a = i / 16 * math.tau + t * 0.3
            cv.line([(cx + math.cos(a) * R * 1.12, cy + math.sin(a) * R * 1.12),
                     (cx + math.cos(a) * R * 1.32, cy + math.sin(a) * R * 1.32)], fill=C["accent"] + (220,), width=8)
        cv.circle(cx, cy, R, fill=C["accent"] + (255,))
    elif obj == "probe":
        k = 1.4 * app
        cv.line([(cx - 900, cy + 300), (cx, cy)], fill=C["muted"] + (140,), width=3)
        cv.circle(cx, cy, 70 * k, fill=C["paper"] + (255,), outline=C["ink"] + (255,), width=5)
        cv.circle(cx, cy, 12 * k, fill=C["ink"] + (255,))
        cv.line([(cx, cy), (cx + 130 * k, cy - 60 * k)], fill=C["ink"] + (255,), width=6)
        cv.line([(cx, cy), (cx - 40 * k, cy + 140 * k)], fill=C["ink"] + (255,), width=6)
        cv.rect(cx - 30 * k, cy + 70 * k, cx + 30 * k, cy + 110 * k, fill=C["sub"] + (255,), radius=6)
    elif obj == "galaxy":
        draw_galaxy(cv, cx, cy, 360 * app, t)
    elif obj == "universe":
        draw_cosmic_web(cv, cx, cy, 340 * app, t)
    rp = seg(t, 0.2, dur)
    draw_rocket(cv, lerp(130, 260, rp), lerp(1110, 1060, rp) + math.sin(t * 3) * 6, -0.35, 60)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=P.get("size", 76))
    for j, (key, y) in enumerate((("distance", 1075), ("light", 1160))):
        if not P.get(key):
            continue
        lp = seg(t, ctx.line_start(P.get(f"{key}_on_line", j), 0.3), 0.45)
        if lp > 0:
            runs = split_emphasis(P[key], P.get("value_emphasis", []), C["ink"], C["accent"])
            cv.rich_line(600, y, runs, 70 if j == 0 else 54, stroke=4, scale=0.7 + 0.3 * ease_out_back(lp),
                         alpha=clamp(lp * 2))


@scene("universe_loop")
def universe_loop(cv: Canvas, t, dur, P, ctx: SceneCtx):
    """Closed universe: a rocket going 'straight' follows the loop and returns to the start marker."""
    cx, cy, R = 540, 800, 310
    cv.circle(cx, cy, R, outline=C["sub"] + (255,), width=10)
    rnd = random.Random(4)
    for _ in range(60):
        a, rr = rnd.uniform(0, math.tau), R * math.sqrt(rnd.random()) * 0.92
        cv.circle(cx + math.cos(a) * rr, cy + math.sin(a) * rr, rnd.uniform(2, 5), fill=C["muted"] + (150,))
    start_a = -math.pi / 2
    sx, sy = cx + math.cos(start_a) * R, cy + math.sin(start_a) * R
    cv.circle(sx, sy, 18, fill=C["accent"] + (255,), outline=C["paper"] + (255,), width=4)
    lp = ease_in_out(seg(t, ctx.line_start(P.get("loop_on_line", 1), dur * 0.3), dur * 0.6))
    a = start_a + lp * math.tau
    for j in range(1, 40):                            # trail along the loop
        q = max(0.0, lp - j * 0.012)
        aa = start_a + q * math.tau
        cv.circle(cx + math.cos(aa) * R, cy + math.sin(aa) * R, 6, fill=C["accent"] + (int(200 * (1 - j / 40)),))
    draw_rocket(cv, cx + math.cos(a) * R, cy + math.sin(a) * R, a + math.pi / 2, 64)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=74)
    if lp >= 0.98 and P.get("arrive_label"):
        ap = seg(t, ctx.line_start(P.get("loop_on_line", 1), dur * 0.3) + dur * 0.6, 0.4)
        cv.text(sx, sy - 70, P["arrive_label"], 52 * (0.7 + 0.3 * ease_out_back(ap)), C["accent"], alpha=clamp(ap * 2),
                stroke=5)
from . import scenes_tokyo  # noqa: E402,F401  (registers the Tokyo scenes)
from . import scenes_imo  # noqa: E402,F401  (registers the yakiimo / Naruto scenes)
from . import scenes_kaiju  # noqa: E402,F401  (registers the voxel kaiju scenes)
