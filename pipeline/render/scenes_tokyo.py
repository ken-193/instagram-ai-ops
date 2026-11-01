"""Scenes for 「もしも阿波踊りが東京を襲撃したら？」: a 2.5D street engine (buildings + crowds in
perspective, camera moves), top-down aerial city, Tokyo Tower at night, townspeople who start dancing,
a Tokyo map that fills with the festival, and the punchline card.

Video colours (sky, buildings, costumes) are natural; UI elements (titles, chips, stamps) use brand roles.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image

from .engine import (C, H, W, Canvas, clamp, ease_in_out, ease_out, ease_out_back, lerp, mix, seg, shake,
                     split_emphasis)
from .scenes import SceneCtx, draw_japan, japan, proj, scene

# ---------------------------------------------------------------- palette (scene colours, not UI)
SKIN = (238, 204, 172)
STRAW = (214, 178, 106)
LANTERN = (255, 198, 112)
AI_BLUE = (38, 62, 118)          # 藍 (Tokushima indigo)
ROBES = [AI_BLUE, C["sub"], C["accent"], (222, 132, 150), (240, 236, 224), (36, 92, 140)]
SKY_DAY = ((206, 222, 214), (247, 238, 222))
SKY_DUSK = ((58, 78, 84), (240, 184, 142))
SKY_NIGHT = ((10, 18, 16), (34, 46, 44))
ASPHALT = (92, 94, 92)


@lru_cache(maxsize=8)
def gradient(ss: int, top: tuple, bottom: tuple) -> Image.Image:
    mask = Image.linear_gradient("L").resize((W * ss, H * ss))
    return Image.composite(Image.new("RGBA", mask.size, bottom + (255,)), Image.new("RGBA", mask.size, top + (255,)),
                           mask)


def sky(cv: Canvas, cols):
    cv.img.paste(gradient(cv.ss, cols[0], cols[1]), (0, 0))


def chip(cv: Canvas, x, y, text, t, live="LIVE", delay=0.0):
    """News-style location chip: [LIVE] 渋谷"""
    p = ease_out(seg(t, delay, 0.35))
    if p <= 0:
        return
    x -= (1 - p) * 60
    lw, _ = cv.text_size(live, 30, family="sans", weight=900)
    tw, _ = cv.text_size(text, 44)
    cv.rect(x, y - 34, x + lw + 34, y + 34, fill=C["accent"] + (int(255 * p),), radius=10)
    cv.text(x + 17 + lw / 2, y, live, 30, C["paper"], family="sans", weight=900, alpha=p, stroke_fill=C["accent"])
    x2 = x + lw + 34
    cv.rect(x2, y - 34, x2 + tw + 40, y + 34, fill=C["paper"] + (int(240 * p),), radius=10)
    cv.text(x2 + 20 + tw / 2, y, text, 44, C["ink"], alpha=p)
    if live and (t * 2) % 1 < 0.6:
        cv.circle(x - 16, y, 8, fill=C["accent"] + (int(255 * p),))


def stamp(cv: Canvas, y, text, emphasis, p, size=70, x0=120, x1=930):
    if p <= 0:
        return
    sx, sy = shake(p * 3, 4 * (1 - p))
    cv.rect(x0 + sx, y - size * 0.95 + sy, x1 + sx, y + size * 0.95 + sy, fill=C["paper"] + (246,),
            outline=C["accent"] + (255,), width=6, radius=22)
    cv.rich_line((x0 + x1) / 2 + sx, y + sy, split_emphasis(text, emphasis, C["ink"], C["accent"]), size,
                 scale=0.6 + 0.4 * ease_out_back(p), alpha=clamp(p * 2))


# ---------------------------------------------------------------- people
def _face(cv: Canvas, x, y, r, mood=1.0, col=None):
    if r < 9:
        return
    col = col or C["ink"]
    k = cv.ss
    for sd in (-1, 1):
        cv.circle(x + sd * r * 0.38, y - r * 0.1, max(1.2, r * 0.11), fill=col + (255,))
    w = r * 0.45
    if mood > 0.2:     # smile
        cv.d.arc([(x - w) * k, (y - r * 0.15) * k, (x + w) * k, (y + r * 0.55) * k], 20, 160, fill=col + (255,),
                 width=max(1, int(r * 0.1 * k)))
    elif mood < -0.2:  # puzzled
        cv.d.arc([(x - w * 0.8) * k, (y + r * 0.35) * k, (x + w * 0.8) * k, (y + r * 0.9) * k], 200, 340,
                 fill=col + (255,), width=max(1, int(r * 0.1 * k)))
    else:
        cv.line([(x - w * 0.6, y + r * 0.4), (x + w * 0.6, y + r * 0.4)], fill=col + (255,), width=max(1, r * 0.1))


def awa_dancer(cv: Canvas, x, y, s, phase, kind=0, ci=0, fog=0.0, fogc=(0, 0, 0), face=True):
    """Awa-odori dancer with feet at (x, y), height s px. The arm and the foot on the SAME side go forward
    together (the dance's signature). kind 0 = 女踊り (yukata, crescent straw hat, hands high),
    kind 1 = 男踊り (happi, low wide stance), kind 2 = 男踊り holding a chōchin lantern.
    Returns the lantern position for kind 2 (for glow), else None."""
    def F(c):
        return mix(c, fogc, fog) if fog > 0 else c
    sn = math.sin(phase)
    side = 1 if sn >= 0 else -1
    amt = abs(sn)
    y = y - amt * s * 0.035
    w = max(1.0, s * 0.045)
    robe, skin, ink = F(ROBES[ci % len(ROBES)]), F(SKIN), F(C["ink"])
    lantern = None
    if s < 16:  # far away: a simple silhouette is enough
        cv.line([(x, y), (x, y - s * 0.7)], fill=robe + (255,), width=max(1.5, s * 0.22))
        cv.circle(x, y - s * 0.8, max(1.2, s * 0.13), fill=F(STRAW if kind == 0 else SKIN) + (255,))
        return None
    if kind == 0:
        neck = y - s * 0.78
        hem = y - s * 0.08
        for sd in (-1, 1):
            fwd = sd == side
            fx = x + sd * s * 0.045 + (side * s * 0.03 if fwd else 0)
            lift = s * 0.05 * amt if fwd else 0
            cv.line([(fx, hem), (fx, y - lift)], fill=ink + (255,), width=w)
        cv.polygon([(x - s * 0.08, neck), (x + s * 0.08, neck), (x + s * 0.115, hem), (x - s * 0.115, hem)],
                   fill=robe + (255,))
        obi = F(C["paper"]) if ci % len(ROBES) in (2, 3) else F(C["accent"])
        cv.polygon([(x - s * 0.088, neck + s * 0.2), (x + s * 0.088, neck + s * 0.2), (x + s * 0.09, neck + s * 0.27),
                    (x - s * 0.09, neck + s * 0.27)], fill=obi + (255,))
        for sd in (-1, 1):
            fwd = sd == side
            sh = (x + sd * s * 0.065, neck + s * 0.04)
            el = (x + sd * s * 0.17, neck - s * 0.05 - (s * 0.03 * amt if fwd else 0))
            hd = (x + sd * s * (0.11 + (0.05 * amt if fwd else 0)), y - s * (1.0 + (0.07 * amt if fwd else 0)))
            cv.line([sh, el], fill=robe + (255,), width=w * 2.0)
            cv.line([el, hd], fill=skin + (255,), width=w * 0.9)
            cv.circle(hd[0], hd[1], w * 0.8, fill=skin + (255,))
        hx, hy = x, neck - s * 0.06
        cv.circle(hx, hy, s * 0.062, fill=skin + (255,))
        if face:
            _face(cv, hx, hy + s * 0.012, s * 0.062, 1.0, ink)
        rx, ry, cy = s * 0.15, s * 0.115, neck - s * 0.085   # 鳥追い笠 (folded straw hat)
        tilt = side * 0.08
        pts = [(hx + rx * math.cos(math.pi + a) + tilt * rx, cy - ry * math.sin(a)) for a in
               (i * math.pi / 14 for i in range(15))]
        cv.polygon(pts, fill=F(STRAW) + (255,), outline=F((170, 132, 70)) + (255,), width=max(1, s * 0.01))
    else:
        neck = y - s * 0.7
        hip = y - s * 0.36
        legc = F((236, 232, 220))
        for sd in (-1, 1):
            fwd = sd == side
            lift = s * 0.07 * amt if fwd else 0
            knee = (x + sd * s * 0.14 + (side * s * 0.03 if fwd else 0), y - s * 0.2 - lift)
            foot = (x + sd * s * 0.12 + (side * s * 0.05 if fwd else 0), y - lift * 0.6)
            cv.line([(x + sd * s * 0.04, hip), knee, foot], fill=legc + (255,), width=w * 1.3)
        cv.polygon([(x - s * 0.09, neck), (x + s * 0.09, neck), (x + s * 0.12, hip + s * 0.03),
                    (x - s * 0.12, hip + s * 0.03)], fill=robe + (255,))
        cv.line([(x, neck), (x, hip)], fill=F(C["paper"]) + (200,), width=max(1, w * 0.5))
        for sd in (-1, 1):
            fwd = sd == side
            sh = (x + sd * s * 0.075, neck + s * 0.04)
            el = (x + sd * s * 0.2, neck + s * 0.04 - (s * 0.06 * amt if fwd else 0))
            hd = (x + sd * s * (0.21 + (0.05 * amt if fwd else 0)), neck - s * (0.1 + (0.12 * amt if fwd else 0)))
            cv.line([sh, el], fill=robe + (255,), width=w * 1.6)
            cv.line([el, hd], fill=skin + (255,), width=w)
            cv.circle(hd[0], hd[1], w * 0.85, fill=skin + (255,))
            if kind == 2 and sd == 1:
                lx, ly = hd[0] + s * 0.03, hd[1] - s * 0.16
                cv.line([hd, (lx, ly)], fill=ink + (255,), width=max(1, w * 0.4))
                cv.rect(lx - s * 0.06, ly - s * 0.02, lx + s * 0.06, ly + s * 0.13, fill=F(LANTERN) + (255,),
                        outline=F(C["accent"]) + (255,), width=max(1, s * 0.01), radius=s * 0.05)
                lantern = (lx, ly + s * 0.055, s * 0.07)
        hx, hy = x, neck - s * 0.075
        cv.circle(hx, hy, s * 0.068, fill=skin + (255,))
        cv.line([(hx - s * 0.07, hy - s * 0.03), (hx + s * 0.07, hy - s * 0.03)], fill=F(C["paper"]) + (255,),
                width=max(1, s * 0.02))
        if face:
            _face(cv, hx, hy + s * 0.015, s * 0.068, 1.0, ink)
    return lantern


TOWN = [(44, 52, 70), (60, 140, 150), (140, 108, 78), (52, 52, 60), (178, 70, 70), (98, 120, 90)]


def townsperson(cv: Canvas, x, y, s, kind, p, phase):
    """A Tokyo pedestrian (0 suit, 1 tourist, 2 coat, 3 student...). p: 0 = standing puzzled -> 1 = dancing."""
    q = ease_in_out(p)
    sn = math.sin(phase) * q
    side = 1 if sn >= 0 else -1
    amt = abs(sn)
    y = y - amt * s * 0.03
    w = max(1.0, s * 0.05)
    body = TOWN[kind % len(TOWN)]
    neck, hip = y - s * 0.76, y - s * 0.4
    for sd in (-1, 1):
        fwd = sd == side and q > 0.3
        lift = s * 0.06 * amt if fwd else 0
        cv.line([(x + sd * s * 0.05, hip), (x + sd * s * (0.07 + 0.05 * q) + (side * s * 0.04 if fwd else 0), y - lift)],
                fill=(40, 40, 46, 255), width=w * 1.3)
    cv.polygon([(x - s * 0.1, neck), (x + s * 0.1, neck), (x + s * 0.11, hip + s * 0.02), (x - s * 0.11, hip + s * 0.02)],
               fill=body + (255,))
    if kind % len(TOWN) == 0:   # suit: shirt + tie
        cv.polygon([(x - s * 0.03, neck), (x + s * 0.03, neck), (x, neck + s * 0.1)], fill=(240, 240, 236, 255))
        cv.polygon([(x - s * 0.012, neck + s * 0.02), (x + s * 0.012, neck + s * 0.02), (x + s * 0.02, neck + s * 0.2),
                    (x, neck + s * 0.23), (x - s * 0.02, neck + s * 0.2)], fill=C["accent"] + (255,))
    if kind % len(TOWN) == 1:   # tourist backpack straps
        cv.line([(x - s * 0.06, neck), (x - s * 0.07, hip)], fill=(120, 84, 50, 255), width=w * 0.6)
        cv.line([(x + s * 0.06, neck), (x + s * 0.07, hip)], fill=(120, 84, 50, 255), width=w * 0.6)
    for sd in (-1, 1):
        fwd = sd == side
        sh = (x + sd * s * 0.09, neck + s * 0.04)
        down_el, down_hd = (x + sd * s * 0.13, neck + s * 0.2), (x + sd * s * 0.14, hip + s * 0.02)
        up_el = (x + sd * s * 0.2, neck - s * 0.02 - (s * 0.04 * amt if fwd else 0))
        up_hd = (x + sd * s * (0.15 + (0.05 * amt if fwd else 0)), y - s * (1.02 + (0.08 * amt if fwd else 0)))
        el = (lerp(down_el[0], up_el[0], q), lerp(down_el[1], up_el[1], q))
        hd = (lerp(down_hd[0], up_hd[0], q), lerp(down_hd[1], up_hd[1], q))
        cv.line([sh, el], fill=body + (255,), width=w * 1.5)
        cv.line([el, hd], fill=SKIN + (255,), width=w * 0.9)
        cv.circle(hd[0], hd[1], w * 0.8, fill=SKIN + (255,))
    if kind % len(TOWN) == 0:   # briefcase: in hand, then dropped at the feet
        if q < 0.3:
            bx, by = x + s * 0.14, hip + s * 0.08
        else:
            bx, by = x + s * 0.24, y - s * 0.06
        cv.rect(bx - s * 0.07, by - s * 0.05, bx + s * 0.07, by + s * 0.06, fill=(70, 50, 36, 255), radius=s * 0.01)
    hx, hy = x + (1 - q) * s * 0.02, neck - s * 0.085
    cv.circle(hx, hy, s * 0.075, fill=SKIN + (255,))
    cv.d.pieslice([(hx - s * 0.078) * cv.ss, (hy - s * 0.082) * cv.ss, (hx + s * 0.078) * cv.ss,
                   (hy + s * 0.05) * cv.ss], 180, 360, fill=(36, 30, 28, 255))
    if kind % len(TOWN) == 1:   # cap
        cv.rect(hx - s * 0.08, hy - s * 0.09, hx + s * 0.11, hy - s * 0.05, fill=C["sub"] + (255,), radius=s * 0.02)
    _face(cv, hx, hy + s * 0.02, s * 0.075, lerp(-1, 1, clamp((q - 0.3) * 3)), C["ink"])
    if q > 0.5:  # festival towel on the shoulder once they join
        cv.line([(x - s * 0.1, neck + s * 0.02), (x + s * 0.02, neck + s * 0.08)], fill=C["paper"] + (255,),
                width=w * 0.9)
    mark = "？" if p < 0.15 else ("！" if p < 0.45 else "♪")
    ma = 1.0 if p < 0.15 else clamp(1 - abs(p - 0.3) * 4) if p < 0.45 else clamp((p - 0.45) * 3)
    if ma > 0:
        cv.text(hx + s * 0.13, hy - s * 0.17, mark, s * 0.17, C["accent"] if mark != "♪" else C["sub"], alpha=ma,
                stroke=3)


# ---------------------------------------------------------------- 2.5D street engine
@dataclass
class Cam:
    vx: float = 540.0     # vanishing point (screen)
    vy: float = 900.0
    f: float = 900.0      # focal length in px
    eye: float = 1.6      # eye height (m)
    z: float = 0.0        # camera position along the street (m)
    x: float = 0.0


NEAR = 2.2


def P3(cam: Cam, X, Y, Z):
    s = cam.f / max(Z - cam.z, 0.05)
    return cam.vx + (X - cam.x) * s, cam.vy - (Y - cam.eye) * s


@lru_cache(maxsize=16)
def street_blocks(seed, z_from, z_to, hmin, hmax, inner=9.0):
    rnd = random.Random(seed)
    out = []
    for side in (-1, 1):
        z = z_from + rnd.uniform(0, 6)
        while z < z_to:
            depth = rnd.uniform(14, 34)
            xi = inner + rnd.uniform(0, 2.5)
            out.append({"side": side, "xi": xi, "xo": xi + rnd.uniform(18, 34), "z0": z, "z1": z + depth,
                        "h": rnd.uniform(hmin, hmax), "tone": rnd.uniform(-1, 1), "seed": rnd.random(),
                        "screen": rnd.random() < 0.28})
            z += depth + rnd.uniform(2, 7)
    return tuple(sorted(out, key=lambda b: -b["z0"]))


def draw_block(cv: Canvas, cam: Cam, b, base_col, fogc, night=0.0, glass=False, screen_fn=None):
    side, xi, xo, z0, z1, h = b["side"], b["xi"], b["xo"], b["z0"], b["z1"], b["h"]
    zmin = cam.z + NEAR
    if z1 <= zmin:
        return
    zc0 = max(z0, zmin)
    fog = clamp((z0 - cam.z - 40) / 320) * 0.8
    col = mix(tuple(int(clamp(c + b["tone"] * 18, 0, 255)) for c in base_col), fogc, fog)
    side_col = mix(mix(col, (255, 255, 255), 0.12 if not night else 0.0), fogc, fog * 0.5)
    Xf = xi * side
    # inner (street-facing) face
    face = [P3(cam, Xf, 0, zc0), P3(cam, Xf, h, zc0), P3(cam, Xf, h, z1), P3(cam, Xf, 0, z1)]
    cv.polygon(face, fill=side_col + (255,))
    s_near = cam.f / (zc0 - cam.z)
    s_far = cam.f / (z1 - cam.z)
    line_col = mix(side_col, (255, 236, 190) if night else (40, 50, 50), 0.35 if not night else 0.55)
    if s_far * 3.5 > 3:
        step = 3.6 if s_far * 3.6 > 5 else 7.2
        y = step
        while y < h:
            cv.line([P3(cam, Xf, y, zc0), P3(cam, Xf, y, z1)], fill=line_col + (150,), width=max(1, s_far * 0.25))
            y += step
        zz = zc0 + 4 - (zc0 % 4)
        while zz < z1:
            cv.line([P3(cam, Xf, 0, zz), P3(cam, Xf, h, zz)], fill=line_col + (110,), width=max(1, s_far * 0.18))
            zz += 4 if glass else 6
    # front face (only when not clipped)
    if z0 >= zmin:
        xa, xb = (-xo, -xi) if side < 0 else (xi, xo)
        (x0, y0), (x1, y1) = P3(cam, xa, h, z0), P3(cam, xb, 0, z0)
        cv.rect(min(x0, x1), y0, max(x0, x1), y1, fill=col + (255,))
        s0 = cam.f / (z0 - cam.z)
        if s0 * 3 > 4:
            y = 3.6
            while y < h:
                yy = P3(cam, 0, y, z0)[1]
                cv.line([(min(x0, x1), yy), (max(x0, x1), yy)], fill=line_col + (120,), width=max(1, s0 * 0.22))
                y += 3.6
        if b["screen"] and screen_fn and s0 > 6 and h > 22:
            sy0, sy1 = P3(cam, 0, min(h - 3, 22), z0)[1], P3(cam, 0, 9, z0)[1]
            pad = abs(x1 - x0) * 0.12
            screen_fn(cv, min(x0, x1) + pad, sy0, max(x0, x1) - pad, sy1)


def draw_street(cv: Canvas, cam: Cam, road=ASPHALT, zebra_at=None, zebra_diag=False, far=500):
    hx = cam.vy - (0 - cam.eye) * cam.f / 4000
    cv.rect(0, hx, W, H, fill=road + (255,))
    for sd in (-1, 1):   # sidewalks
        cv.polygon([P3(cam, sd * 6.5, 0, cam.z + NEAR), P3(cam, sd * 9.5, 0, cam.z + NEAR), P3(cam, sd * 9.5, 0, cam.z + far),
                    P3(cam, sd * 6.5, 0, cam.z + far)], fill=mix(road, (200, 196, 186), 0.6) + (255,))
    z = math.floor(cam.z / 9) * 9 + 3
    while z < cam.z + 160:   # centre dashes
        if z > cam.z + NEAR:
            cv.polygon([P3(cam, -0.15, 0, z), P3(cam, 0.15, 0, z), P3(cam, 0.15, 0, z + 4), P3(cam, -0.15, 0, z + 4)],
                       fill=(222, 218, 200, 220))
        z += 9
    if zebra_at:
        z0 = zebra_at
        if z0 > cam.z + NEAR:
            for i in range(14):
                xa = -6.3 + i * 0.95
                cv.polygon([P3(cam, xa, 0, z0), P3(cam, xa + 0.5, 0, z0), P3(cam, xa + 0.5, 0, z0 + 4),
                            P3(cam, xa, 0, z0 + 4)], fill=(236, 234, 226, 235))
        if zebra_diag:   # diagonal crossing (ladder of bars along the diagonal)
            ca, sa = math.cos(0.7), math.sin(0.7)
            for i in range(9):
                u = 2 + i * 1.6
                cx, cz = -5 + u * ca, z0 + 6 + u * sa * 1.8
                pts = [(cx - 0.4 * ca - 2.2 * sa, cz - 0.4 * sa + 2.2 * ca), (cx + 0.4 * ca - 2.2 * sa, cz + 0.4 * sa + 2.2 * ca),
                       (cx + 0.4 * ca + 2.2 * sa, cz + 0.4 * sa - 2.2 * ca), (cx - 0.4 * ca + 2.2 * sa, cz - 0.4 * sa - 2.2 * ca)]
                cv.polygon([P3(cam, x, 0, zz) for x, zz in pts], fill=(236, 234, 226, 200))


@lru_cache(maxsize=8)
def crowd_seed(n_rows, per_row, seed=3, width=6.0):
    rnd = random.Random(seed)
    rows = []
    for r in range(n_rows):
        row = []
        for c in range(per_row):
            x = -width + (2 * width) * (c + 0.5 + rnd.uniform(-0.35, 0.35)) / per_row
            row.append((x, rnd.uniform(-0.35, 0.35), rnd.choice((0, 0, 1, 1, 2)), rnd.uniform(0, 6.3),
                        rnd.randrange(len(ROBES)), rnd.uniform(0.92, 1.08)))
        rows.append(row)
    return rows


def draw_crowd3(cv: Canvas, cam: Cam, t, front, spacing=1.6, n_rows=120, per_row=9, fogc=(255, 255, 255),
                width=6.0, max_z=700, march=0.0, lanterns=None):
    """Rows of dancers filling the street from Z=front backwards; drawn far -> near."""
    rows = crowd_seed(n_rows, per_row, 3, width)
    for r in range(n_rows - 1, -1, -1):
        Zr = front + r * spacing - march * t
        if Zr - cam.z < NEAR + 0.6 or Zr - cam.z > max_z:
            continue
        sc = cam.f / (Zr - cam.z)
        fog = clamp((Zr - cam.z - 30) / 300) * 0.75
        for (x, dz, kind, ph, ci, hs) in rows[r]:
            X, Z = x, Zr + dz
            px, py = P3(cam, X, 0, Z)
            if px < -80 or px > W + 80:
                continue
            s = 1.65 * hs * sc
            lt = awa_dancer(cv, px, py, s, t * 6.4 + ph, kind, ci, fog, fogc, face=s > 150)
            if lt is not None and lanterns is not None:
                lanterns.append(lt)


def lantern_glow(cv: Canvas, pts, strength=0.8, radius=22):
    if not pts:
        return
    cv.glow(lambda d, k: [d.ellipse([(x - r * 1.6) * k, (y - r * 1.6) * k, (x + r * 1.6) * k, (y + r * 1.6) * k],
                                    fill=LANTERN + (255,)) for x, y, r in pts], radius=radius, strength=strength)


def screen_content(text, t, emph=False):
    def fn(cv: Canvas, x0, y0, x1, y1):
        cv.rect(x0, y0, x1, y1, fill=(22, 30, 28, 255), outline=(60, 70, 66, 255), width=max(1, (x1 - x0) * 0.02))
        hgt = y1 - y0
        if hgt < 14:
            return
        if (t * 3) % 1 < 0.15:
            cv.rect(x0, y0, x1, y1, fill=C["accent"] + (120,))
        size = min(hgt * 0.45, (x1 - x0) / max(1, len(text)) * 0.9)
        cv.text((x0 + x1) / 2, (y0 + y1) / 2, text, size, C["accent"] if emph else C["paper"],
                stroke_fill=(22, 30, 28))
    return fn


# ---------------------------------------------------------------- s1: title + something approaching
@scene("tokyo_alert")
def tokyo_alert(cv: Canvas, t, dur, P, ctx: SceneCtx):
    sky(cv, SKY_DAY)
    amp = 1.5 + 5 * ease_in_out(t / max(dur, 0.1)) * (0.6 + 0.4 * abs(math.sin(t * 9.4)))
    sx, sy = shake(t, amp)
    cam = Cam(vx=540 + sx, vy=930 + sy, f=900, eye=P.get("eye", 6.0), z=-t * 0.6)
    fogc = SKY_DAY[1]
    draw_street(cv, cam, zebra_at=7, zebra_diag=True)
    for b in street_blocks(11, 4, 420, 18, 70):
        draw_block(cv, cam, b, (150, 146, 136), fogc, screen_fn=screen_content(P.get("screen", "速報"), t, True))
    front = lerp(P.get("crowd_from", 260), P.get("crowd_to", 10), ease_out(seg(t, 0.0, dur)))
    lts = []
    draw_crowd3(cv, cam, t, front, n_rows=140, fogc=fogc, lanterns=lts)
    lantern_glow(cv, lts, 0.5, 14)
    # title: shown from the very first frame (never animated in)
    lines = P.get("title", ["もしも阿波踊りが", "東京を襲撃したら？"])
    size = P.get("title_size", 88)
    y0 = P.get("title_y", 700)
    cx = 540 - 48  # centre of the Reels safe area
    br = 1 + 0.015 * math.sin(t * 2.2)
    for i, ln in enumerate(lines):
        cv.rich_line(cx, y0 + i * size * 1.32, split_emphasis(ln, P.get("emphasis", []), C["ink"], C["accent"]), size,
                     stroke=9, scale=br)
    # breaking-news bar
    cv.rect(0, 240, W, 312, fill=C["accent"] + (255,))
    cv.text(96, 276, P.get("banner", "緊急速報"), 46, C["paper"], anchor="lm", stroke_fill=C["accent"])
    cv.rect(0, 312, W, 364, fill=(36, 44, 40, 235))
    tick = P.get("ticker", "")
    if tick:
        tw, _ = cv.text_size(tick, 34, family="sans", weight=800)
        x = W - ((t * 220) % (tw + W))
        cv.text(x, 338, tick, 34, C["paper"], family="sans", weight=800, anchor="lm", stroke_fill=(36, 44, 40))
    if (t * 2) % 1 < 0.6:
        cv.circle(W - 210, 276, 10, fill=C["paper"] + (255,))


# ---------------------------------------------------------------- top-down aerial city
@lru_cache(maxsize=4)
def city_grid(seed, half=700, block=86.0, road=22.0):
    rnd = random.Random(seed)
    blocks = []
    pitch = block + road
    n = int(half / pitch) + 2
    for i in range(-n, n):
        for j in range(-n, n):
            x0, y0 = i * pitch + road / 2, j * pitch + road / 2
            # split a block into 1-3 buildings
            parts = rnd.choice((1, 2, 2, 3))
            for k in range(parts):
                bx0 = x0 + k * block / parts + 2
                bx1 = x0 + (k + 1) * block / parts - 2
                inset = rnd.uniform(2, 10)
                blocks.append((bx0, y0 + inset, bx1, y0 + block - inset, rnd.uniform(-1, 1), rnd.uniform(4, 30)))
    return tuple(blocks), pitch, road


@lru_cache(maxsize=4)
def road_people(seed, n, half=700, pitch=108.0, road=22.0):
    rnd = random.Random(seed)
    pts = []
    while len(pts) < n:
        if rnd.random() < 0.5:   # vertical road
            gx = round(rnd.uniform(-half, half) / pitch) * pitch
            x, y = gx + rnd.uniform(-road / 2 + 1.5, road / 2 - 1.5), rnd.uniform(-half, half)
        else:
            gy = round(rnd.uniform(-half, half) / pitch) * pitch
            x, y = rnd.uniform(-half, half), gy + rnd.uniform(-road / 2 + 1.5, road / 2 - 1.5)
        pts.append((x, y, rnd.random(), rnd.randrange(len(ROBES)), rnd.uniform(0, 6.3)))
    return tuple(pts)


def aerial_xf(cx, cy, scale, rot):
    ca, sa = math.cos(rot), math.sin(rot)

    def f(x, y):
        x, y = x - cx, y - cy
        return 540 + (x * ca - y * sa) * scale, 760 + (x * sa + y * ca) * scale
    return f


def draw_aerial_city(cv: Canvas, xf, scale, blocks, shadow=(0.35, 0.5)):
    cv.rect(0, 0, W, H, fill=(108, 110, 106, 255))
    for (x0, y0, x1, y1, tone, hgt) in blocks:
        c = [xf(x0, y0), xf(x1, y0), xf(x1, y1), xf(x0, y1)]
        if all(px < -60 for px, _ in c) or all(px > W + 60 for px, _ in c) or all(py < -60 for _, py in c) or \
                all(py > H + 60 for _, py in c):
            continue
        off = hgt * shadow[0] * scale, hgt * shadow[1] * scale
        cv.polygon([(px + off[0], py + off[1]) for px, py in c], fill=(70, 72, 70, 140))
        base = (200, 194, 180) if tone > 0.3 else (176, 182, 178) if tone > -0.4 else (150, 156, 160)
        cv.polygon(c, fill=base + (255,), outline=(120, 120, 116, 255), width=max(1, scale * 0.6))
        if scale > 1.5 and hgt > 18:   # rooftop unit
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            cv.polygon([xf(mx - 6, my - 5), xf(mx + 6, my - 5), xf(mx + 6, my + 5), xf(mx - 6, my + 5)],
                       fill=mix(base, (90, 90, 90), 0.3) + (255,))


def draw_top_people(cv: Canvas, xf, scale, pts, t, visible, r=4.4):
    k = cv.ss
    layer, d = cv.overlay()
    rr = r * max(0.7, min(1.6, scale / 2.5))
    lts = []
    for i, (x, y, rnd, ci, ph) in enumerate(pts):
        if not visible(x, y, rnd):
            continue
        jx = math.sin(t * 6.4 + ph) * 0.9
        px, py = xf(x + jx, y + math.cos(t * 5 + ph) * 0.5)
        if px < -10 or px > W + 10 or py < -10 or py > H + 10:
            continue
        col = ROBES[ci]
        d.ellipse([(px - rr * 0.9) * k, (py - rr * 0.2) * k, (px + rr * 0.9) * k, (py + rr * 1.5) * k], fill=col + (255,))
        d.ellipse([(px - rr) * k, (py - rr) * k, (px + rr) * k, (py + rr * 0.6) * k], fill=STRAW + (255,))
        if i % 23 == 0:
            lts.append((px, py, rr))
    cv.img.alpha_composite(layer)
    return lts


@scene("aerial_wave")
def aerial_wave(cv: Canvas, t, dur, P, ctx: SceneCtx):
    blocks, pitch, road = city_grid(5)
    p = ease_in_out(t / max(dur, 0.1))
    scale = lerp(P.get("scale_from", 2.9), P.get("scale_to", 1.9), p)
    xf = aerial_xf(0, lerp(80, -40, p), scale, lerp(-0.12, 0.05, p))
    draw_aerial_city(cv, xf, scale, blocks)
    front = lerp(520, -620, ease_in_out(seg(t, 0, dur * 1.05)))
    pts = road_people(7, 5200, 700, pitch, road)
    lts = draw_top_people(cv, xf, scale, pts, t, lambda x, y, r: y > front + r * 90)
    lantern_glow(cv, lts, 0.55, 10)
    chip(cv, 96, 410, P.get("chip", "東京上空"), t, P.get("live", "LIVE"))
    sp = seg(t, ctx.line_start(P.get("stamp_on_line", 1), dur * 0.5) + P.get("stamp_delay", 1.0), 0.45)
    stamp(cv, 1060, P.get("stamp", ""), P.get("stamp_emphasis", []), sp, size=72)


# ---------------------------------------------------------------- s3: Shibuya
@lru_cache(maxsize=2)
def scramble_people(n, seed=13):
    rnd = random.Random(seed)
    pts = []
    while len(pts) < n:
        x, y = rnd.uniform(-420, 420), rnd.uniform(-700, 700)
        if abs(x) < 26 or abs(y) < 26 or (abs(x) < 60 and abs(y) < 60):
            pts.append((x, y, rnd.random(), rnd.randrange(len(ROBES)), rnd.uniform(0, 6.3)))
    return tuple(pts)


def draw_scramble(cv: Canvas, xf, scale):
    cv.rect(0, 0, W, H, fill=(104, 106, 104, 255))
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    rnd = random.Random(4)
    for sx, sy in corners:   # four big corner blocks with buildings
        for k in range(5):
            x0 = sx * (34 + k * 70 + rnd.uniform(0, 8))
            x1 = sx * (34 + k * 70 + 62)
            for m in range(6):
                y0 = sy * (34 + m * 110 + rnd.uniform(0, 8))
                y1 = sy * (34 + m * 110 + 100)
                hgt = rnd.uniform(10, 50)
                c = [xf(x0, y0), xf(x1, y0), xf(x1, y1), xf(x0, y1)]
                off = hgt * 0.35 * scale, hgt * 0.5 * scale
                cv.polygon([(px + off[0], py + off[1]) for px, py in c], fill=(70, 72, 70, 130))
                tone = rnd.random()
                base = (206, 198, 182) if tone > 0.6 else (178, 184, 180) if tone > 0.25 else (148, 152, 160)
                cv.polygon(c, fill=base + (255,), outline=(118, 118, 114, 255), width=max(1, scale * 0.6))
    for sd in (-1, 1):       # straight crossings on all four sides
        for i in range(10):
            a = -24 + i * 5
            cv.polygon([xf(a, sd * 30), xf(a + 2.6, sd * 30), xf(a + 2.6, sd * 44), xf(a, sd * 44)], fill=(236, 234, 226, 230))
            cv.polygon([xf(sd * 30, a), xf(sd * 44, a), xf(sd * 44, a + 2.6), xf(sd * 30, a + 2.6)], fill=(236, 234, 226, 230))
    for diag in (1, -1):     # the diagonal "scramble" crossings
        ca, sa = math.cos(math.pi / 4 * diag), math.sin(math.pi / 4 * diag)
        for i in range(-9, 10):
            if abs(i) < 1:
                continue
            cx, cy = i * 3.6 * ca, i * 3.6 * sa
            cv.polygon([xf(cx + a * 0.8 * ca - b * 5 * sa, cy + a * 0.8 * sa + b * 5 * ca)
                        for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))], fill=(236, 234, 226, 170))


@scene("shibuya_scramble")
def shibuya_scramble(cv: Canvas, t, dur, P, ctx: SceneCtx):
    split = ctx.line_start(P.get("aerial_on_line", 1), dur * 0.4) + P.get("aerial_delay", 0.0)
    if t < split:     # A: low angle, looking up between buildings while dancers pass in front
        sky(cv, SKY_DAY)
        cam = Cam(vx=540, vy=990, f=640, eye=1.0, z=-4 - t * 1.2)
        fogc = SKY_DAY[1]
        draw_street(cv, cam)
        for b in street_blocks(23, 2, 300, 40, 95, 8.0):
            draw_block(cv, cam, b, (140, 140, 134), fogc, screen_fn=screen_content(P.get("screen", "阿波踊り"), t, True))
        lts = []
        for row, (Z, n, sp) in enumerate(((7.0, 9, 1.4), (4.6, 7, 1.7), (2.6, 5, 2.0))):
            for i in range(n):
                X = ((i * (24 / n) + t * sp + row * 2.1) % 24) - 12
                px, py = P3(cam, X, 0, Z + cam.z)
                s = 1.65 * cam.f / Z
                lt = awa_dancer(cv, px, py, s, t * 6.4 + i * 1.3 + row, (i + row) % 3, (i * 2 + row) % len(ROBES))
                if lt:
                    lts.append(lt)
        lantern_glow(cv, lts, 0.6, 20)
    else:             # B: drone above the scramble crossing, crowd keeps thickening
        tb = t - split
        q = ease_in_out(tb / max(dur - split, 0.1))
        scale = lerp(3.4, 2.6, q)
        xf = aerial_xf(0, 0, scale, lerp(0.2, 0.42, q))
        draw_scramble(cv, xf, scale)
        fill = ease_out(seg(tb, 0, max(0.5, dur - split - 0.4)))
        lts = draw_top_people(cv, xf, scale, scramble_people(4200), t,
                              lambda x, y, r: r < 0.25 + 0.75 * fill and (abs(x) + abs(y)) < 120 + fill * 900)
        lantern_glow(cv, lts, 0.5, 10)
        if tb < 0.18:
            cv.rect(0, 0, W, H, fill=(255, 255, 255, int(255 * (1 - tb / 0.18))))
    chip(cv, 96, 410, P.get("chip", "渋谷"), t, P.get("live", "LIVE"))


# ---------------------------------------------------------------- s4: Shinjuku canyon (dolly forward)
@scene("shinjuku_canyon")
def shinjuku_canyon(cv: Canvas, t, dur, P, ctx: SceneCtx):
    sky(cv, SKY_DUSK)
    beat = 60 / P.get("bpm", 128) * 2
    hit = (t % beat) / beat
    sx, sy = shake(t, 3 * (1 - hit) ** 3)
    cam = Cam(vx=540 + sx, vy=820 + sy, f=820, eye=6.0 + t * 0.6, z=t * P.get("speed", 9.0))
    fogc = SKY_DUSK[1]
    draw_street(cv, cam, road=(84, 82, 84))
    for b in street_blocks(37, 5, 640, 90, 230, 9.5):
        draw_block(cv, cam, b, (96, 112, 124), fogc, night=0.3, glass=True)
    lts = []
    draw_crowd3(cv, cam, t, 14, spacing=1.5, n_rows=220, per_row=9, fogc=fogc, max_z=600, march=1.2, lanterns=lts)
    lantern_glow(cv, lts, 0.6, 16)
    for k in range(3):   # taiko shock rings from the vanishing point
        ph = ((t / beat) + k / 3) % 1
        r = 40 + ph * 900
        cv.circle(cam.vx, cam.vy, r, outline=LANTERN + (int(120 * (1 - ph)),), width=4)
    chip(cv, 96, 410, P.get("chip", "新宿"), t, P.get("live", "LIVE"))


# ---------------------------------------------------------------- s5: Tokyo Tower at night
def tower_half_width(y, base, top):
    f = clamp((y - top) / (base - top))
    return 14 + 236 * f ** 1.9


def draw_tower(cv: Canvas, cx, base, top, scale=1.0, lit=1.0):
    """Lattice tower silhouette (orange-red + white bands), lit at night."""
    def X(dx):
        return cx + dx * scale

    def Y(y):
        return base - (base - y) * scale
    tip = top - 230
    red, white = C["accent"], (246, 240, 230)
    seg_n = 12
    for i in range(seg_n):
        ya, yb = lerp(base, top, i / seg_n), lerp(base, top, (i + 1) / seg_n)
        wa, wb = tower_half_width(ya, base, top), tower_half_width(yb, base, top)
        col = white if i % 3 == 2 else red
        col = mix(col, (255, 220, 160), 0.15 * lit)
        th = max(3, 16 * (1 - i / seg_n)) * scale
        for sd in (-1, 1):
            cv.polygon([(X(sd * wa), Y(ya)), (X(sd * (wa - th * 1.6)), Y(ya)), (X(sd * (wb - th)), Y(yb)), (X(sd * wb), Y(yb))],
                       fill=col + (255,))
        cv.line([(X(-wa), Y(ya)), (X(wb), Y(yb))], fill=col + (230,), width=max(1.5, 4 * scale * (1 - i / seg_n * 0.7)))
        cv.line([(X(wa), Y(ya)), (X(-wb), Y(yb))], fill=col + (230,), width=max(1.5, 4 * scale * (1 - i / seg_n * 0.7)))
        cv.line([(X(-wb), Y(yb)), (X(wb), Y(yb))], fill=col + (255,), width=max(1.5, 3 * scale))
    # arch between the legs
    w0 = tower_half_width(base - 120, base, top)
    cv.d.arc([X(-w0 * 0.9) * cv.ss, Y(base - 150) * cv.ss, X(w0 * 0.9) * cv.ss, Y(base + 90) * cv.ss], 180, 360,
             fill=red + (255,), width=int(10 * scale * cv.ss))
    for yd, wd, hd in ((lerp(base, top, 0.42), 1.0, 34), (lerp(base, top, 0.78), 1.0, 22)):   # observation decks
        wdk = tower_half_width(yd, base, top) + 22
        cv.rect(X(-wdk), Y(yd - hd), X(wdk), Y(yd + hd * 0.3), fill=(250, 244, 230, 255), outline=red + (255,),
                width=max(1, 3 * scale), radius=4 * scale)
        for k in range(8):
            wx = X(-wdk + (k + 0.5) * (2 * wdk / 8))
            cv.rect(wx - 6 * scale, Y(yd - hd * 0.7), wx + 6 * scale, Y(yd - hd * 0.1), fill=LANTERN + (int(255 * lit),))
    cv.polygon([(X(-14), Y(top)), (X(14), Y(top)), (X(5), Y(tip)), (X(-5), Y(tip))], fill=red + (255,))
    cv.line([(X(0), Y(tip)), (X(0), Y(tip - 70))], fill=white + (255,), width=max(1.5, 4 * scale))


@lru_cache(maxsize=2)
def night_city(seed=8):
    rnd = random.Random(seed)
    out = []
    x = -200
    while x < 2400:
        w = rnd.uniform(40, 120)
        out.append((x, w, rnd.uniform(60, 330), rnd.random()))
        x += w + rnd.uniform(-10, 14)
    return tuple(out)


@scene("tower_night")
def tower_night(cv: Canvas, t, dur, P, ctx: SceneCtx):
    sky(cv, SKY_NIGHT)
    rnd = random.Random(2)
    for _ in range(70):
        x, y = rnd.uniform(0, W), rnd.uniform(0, 700)
        cv.circle(x, y, rnd.uniform(0.8, 2.0), fill=(230, 230, 210, int(120 + 100 * math.sin(t * 2 + x))))
    q = ease_in_out(t / max(dur, 0.1))
    base = lerp(1120, 1150, q)
    tilt = lerp(0.2, 0.36, q)          # drone rises -> rings open up
    pan = t * 55
    horizon = base - 40
    for (x, w, h, tone) in night_city():   # skyline (parallax = orbit)
        xx = ((x - pan) % 2600) - 200
        c = mix((20, 30, 30), (40, 54, 52), tone)
        cv.rect(xx, horizon - h, xx + w, horizon + 10, fill=c + (255,))
        for j in range(int(h / 22)):
            if (j * 7 + int(x)) % 3 == 0:
                cv.rect(xx + 8, horizon - h + 10 + j * 22, xx + w - 8, horizon - h + 14 + j * 22,
                        fill=LANTERN + (110,))
    cv.rect(0, horizon + 8, W, H, fill=(16, 24, 22, 255))
    cv.glow(lambda d, k: d.ellipse([140 * k, (base - 110) * k, 940 * k, (base + 160) * k], fill=LANTERN + (255,)),
            radius=60, strength=0.35 + 0.25 * q)
    rings = P.get("rings", 9)
    lit_rings = 1 + int((rings - 1) * ease_out(seg(t, 0.3, dur * 0.7)))
    front_pts, back_pts = [], []
    for rk in range(rings):
        if rk >= lit_rings:
            break
        rx = 170 + rk * 70
        n = int(rx / 7)
        w = (0.35 if rk % 2 else -0.28) * (1 + rk * 0.05)
        for i in range(n):
            a = i / n * math.tau + t * w + rk
            x, y = 540 + rx * math.cos(a), base + rx * tilt * math.sin(a)
            (front_pts if math.sin(a) > 0 else back_pts).append((x, y, 3.2 + rk * 0.25, i + rk))
    sc = lerp(0.98, 1.06, q)
    top = base - 650

    def draw_ring_pts(pts):
        for x, y, r, i in pts:
            cv.line([(x, y), (x, y - r * 3.2)], fill=(14, 20, 20, 255), width=r * 1.2)
            cv.circle(x, y - r * 4.2, r, fill=LANTERN + (255,))
    draw_ring_pts(back_pts)
    lantern_glow(cv, [(x, y - r * 4.2, r) for x, y, r, _ in back_pts], 0.45 + 0.3 * q, 12)
    draw_tower(cv, 540, base, top, sc, lit=1.0)
    cv.glow(lambda d, k: d.line([(540 * k, (base - 650 * sc) * k), (540 * k, base * k)], fill=C["accent"] + (255,),
                                width=int(40 * k)), radius=40, strength=0.35)
    draw_ring_pts(front_pts)
    lantern_glow(cv, [(x, y - r * 4.2, r) for x, y, r, _ in front_pts], 0.55 + 0.3 * q, 12)
    chip(cv, 96, 410, P.get("chip", "東京タワー"), t, P.get("live", "LIVE"))


# ---------------------------------------------------------------- s6: people start dancing
@scene("dance_spread")
def dance_spread(cv: Canvas, t, dur, P, ctx: SceneCtx):
    sky(cv, SKY_DUSK)
    cam = Cam(vx=540, vy=800, f=760, eye=1.7, z=t * 0.3)
    fogc = SKY_DUSK[1]
    draw_street(cv, cam, road=(88, 86, 86))
    for b in street_blocks(51, 6, 360, 22, 70, 9.0):
        draw_block(cv, cam, b, (128, 120, 112), fogc, night=0.6)
    lts = []
    draw_crowd3(cv, cam, t, 22, spacing=1.6, n_rows=120, fogc=fogc, lanterns=lts)
    for k in range(6):   # festival lantern strings across the street
        Z = cam.z + 6 + k * 9
        pts = [P3(cam, -9 + i * 1.5, 6.5 - 0.9 * math.sin(i / 12 * math.pi), Z) for i in range(13)]
        cv.line(pts, fill=(40, 30, 26, 200), width=max(1, 30 / (Z - cam.z)))
        for (x, y) in pts[1:-1]:
            r = 0.32 * cam.f / (Z - cam.z)
            cv.rect(x - r * 0.7, y, x + r * 0.7, y + r * 2, fill=LANTERN + (255,), outline=C["accent"] + (255,),
                    width=max(1, r * 0.1), radius=r * 0.6)
            lts.append((x, y + r, r * 0.8))
    lantern_glow(cv, lts, 0.65, 16)
    start = ctx.line_start(P.get("spread_on_line", 1), dur * 0.4) - 0.2
    rows = P.get("rows", [(1000, 200, 6), (1085, 255, 5), (1185, 320, 4)])
    order = random.Random(17)
    idx = 0
    for ry, rs, n in rows:
        for i in range(n):
            x = 120 + (840 / max(1, n - 1)) * i + (35 if n % 2 == 0 else 0) - 17
            kind = (i + int(ry)) % len(TOWN)
            delay = order.uniform(0, 1.6)
            if idx == 3:
                tp = ctx.line_start(0, 0) + 1.2     # the first one gives in early
            else:
                tp = start + delay
            p = seg(t, tp, 0.6)
            townsperson(cv, x, ry, rs, kind, p, t * 6.4 + i)
            idx += 1


# ---------------------------------------------------------------- s7: all of Tokyo
TOKYO_BB = (138.9, 139.95, 35.48, 35.92)
SHINJUKU = (139.70, 35.69)


@lru_cache(maxsize=2)
def tokyo_points(n, seed=19):
    rings = []
    for p in japan():
        if p["iso"] != "JP-13":
            continue
        for r in p["rings"]:
            xs, ys = [x for x, _ in r], [y for _, y in r]
            if max(xs) > TOKYO_BB[0] and min(xs) < TOKYO_BB[1] and max(ys) > TOKYO_BB[2] and min(ys) < TOKYO_BB[3]:
                rings.append(r)

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
        x, y = rnd.uniform(TOKYO_BB[0], TOKYO_BB[1]), rnd.uniform(TOKYO_BB[2], TOKYO_BB[3])
        if inside(x, y):
            d = math.hypot((x - SHINJUKU[0]) * 0.81, y - SHINJUKU[1])
            pts.append((x, y, d, rnd.random(), rnd.randrange(len(ROBES)), rnd.uniform(0, 6.3)))
    return tuple(pts)


@scene("tokyo_festival")
def tokyo_festival(cv: Canvas, t, dur, P, ctx: SceneCtx):
    q = ease_in_out(seg(t, 0, dur * 0.8))
    cam = (lerp(139.70, 139.43, q), lerp(35.69, 35.70, q), math.exp(lerp(math.log(3000), math.log(1180), q)))
    draw_japan(cv, cam, highlight="JP-13", hl_color=C["sub_light"], hl_alpha=1.0)
    fill = ease_in_out(seg(t, 0.1, dur * 0.75))
    reach = 0.03 + fill * 0.75
    k = cv.ss
    layer, d = cv.overlay()
    lts = []
    for i, (lo, la, dist, rnd, ci, ph) in enumerate(tokyo_points(2600)):
        if dist > reach * (0.75 + 0.25 * rnd):
            continue
        x, y = proj(lo, la, cam)
        if x < -10 or x > W + 10 or y < 0 or y > H:
            continue
        x += math.sin(t * 6.4 + ph) * 1.4
        r = 3.6
        d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k], fill=ROBES[ci] + (240,))
        if i % 14 == 0:
            lts.append((x, y, 3))
    cv.img.alpha_composite(layer)
    lantern_glow(cv, lts, 0.5, 9)
    # elapsed time + share of people dancing (fiction counters)
    mins = int(round(30 * fill))
    pct = int(round(100 * fill))
    cv.rect(96, 360, 520, 452, fill=C["paper"] + (240,), outline=C["sub"] + (255,), width=3, radius=18)
    cv.text(120, 406, P.get("clock_label", "経過"), 38, C["muted"], anchor="lm")
    cv.text(500, 406, f"{mins}{P.get('clock_unit', '分')}", 64, C["accent"], anchor="rm", stroke=3)
    cv.rect(96, 470, 912, 540, fill=C["paper"] + (240,), outline=C["sub"] + (255,), width=3, radius=18)
    cv.text(120, 505, P.get("bar_label", "踊っている人"), 34, C["ink"], anchor="lm")
    cv.rect(400, 490, 400 + 380 * fill, 520, fill=C["sub"] + (255,), radius=10)
    cv.text(898, 505, f"{pct}{P.get('bar_unit', '％')}", 40, C["accent"], anchor="rm", stroke=3)
    sp = seg(t, ctx.line_start(0, 0) + P.get("stamp_at", dur * 0.72), 0.45)
    stamp(cv, 1090, P.get("stamp", ""), P.get("stamp_emphasis", []), sp, size=68)


# ---------------------------------------------------------------- s8: punchline card
@scene("branch_ochi")
def branch_ochi(cv: Canvas, t, dur, P, ctx: SceneCtx):
    sky(cv, SKY_DUSK)
    horizon = 1000
    for (x, w, h, tone) in night_city(4):
        xx = x * 0.5 - 100 - t * 8
        c = mix((52, 62, 66), (78, 88, 90), tone)
        cv.rect(xx, horizon - h * 0.8, xx + w * 0.5, horizon + 10, fill=c + (255,))
    draw_tower(cv, 820, horizon + 5, horizon - 330, 0.45, lit=0.6)
    cv.rect(0, horizon, W, H, fill=(70, 66, 64, 255))
    lts = []
    for row, (yy, s, n) in enumerate(((1080, 120, 11), (1170, 170, 8), (1290, 230, 6))):
        for i in range(n):
            x = 60 + (960 / (n - 1)) * i + (row % 2) * 30
            lt = awa_dancer(cv, x, yy, s, t * 6.4 + i * 1.1 + row, (i + row) % 3, (i + row * 2) % len(ROBES))
            if lt:
                lts.append(lt)
    lantern_glow(cv, lts, 0.6, 18)
    p = seg(t, ctx.line_start(0, 0.2) - 0.1, 0.5)
    if p > 0:
        sx, sy = shake(t, 6 * (1 - p))
        sc = 0.7 + 0.3 * ease_out_back(p)
        x0, x1, y0, y1 = 96, 912, 470, 900
        cv.rect(x0 + sx, y0 + sy, x1 + sx, y1 + sy, fill=C["paper"] + (int(246 * clamp(p * 2)),),
                outline=C["sub"] + (255,), width=8, radius=28)
        for i, ln in enumerate(P.get("lines", ["東京、", "徳島支部に", "なりました。"])):
            cv.rich_line(504 + sx, 575 + i * 112 + sy, split_emphasis(ln, P.get("emphasis", []), C["ink"], C["accent"]),
                         P.get("size", 92), scale=sc, alpha=clamp(p * 2))
    sp = seg(t, ctx.line_start(0, 0.2) + P.get("plate_delay", 1.6), 0.4)
    if sp > 0 and P.get("plate"):
        sx, sy = shake(t, 3 * (1 - sp))
        cv.rect(560 + sx, 920 + sy, 900 + sx, 990 + sy, fill=C["sub"] + (255,), radius=12)
        cv.text(730 + sx, 955 + sy, P["plate"], 40 * (0.7 + 0.3 * ease_out_back(sp)), C["paper"], alpha=clamp(sp * 2),
                stroke_fill=C["sub"])
