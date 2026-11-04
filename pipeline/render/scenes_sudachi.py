"""「もしも桃太郎がすだちから生まれたら？」 — rounded, softly shaded 2.5D characters (no blocks) with
cinematic 2D camera moves (low angles, dolly-ins, orbit-like parallax, shake, slow motion).

All drawing is in screen pixels through a Cam2 (centre, zoom, shake); characters are built from shaded
ellipses / capsules so they read as soft 3D toys.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image

from .engine import C, H, W, Canvas, clamp, ease_in_out, ease_out, ease_out_back, lerp, mix, seg, shake, split_emphasis
from .scenes import SceneCtx, scene
from .scenes_tokyo import gradient, sky

SUDACHI = (64, 150, 38)
SUDACHI_D = (36, 104, 24)
FLESH = (226, 238, 150)
SKIN = (246, 210, 178)
HAIR = (34, 30, 30)
HAORI = (46, 140, 62)
HAKAMA = (232, 222, 190)
WHITE = (250, 248, 240)
ONI = (214, 62, 46)
ONI_D = (150, 34, 28)
GOLD = (246, 200, 60)
DOG = (240, 214, 170)
MONKEY = (150, 96, 60)
MFACE = (244, 170, 150)
KIJI = (40, 110, 80)
KIJI_RED = (214, 40, 34)
GLOW = (170, 255, 120)


# ---------------------------------------------------------------- shaded primitives
def ell(cv: Canvas, x, y, rx, ry, col, a=255, rot=0.0, n=44):
    if rx < 0.4 or ry < 0.4:
        return
    c, s = math.cos(rot), math.sin(rot)
    pts = [(x + rx * math.cos(u) * c - ry * math.sin(u) * s, y + rx * math.cos(u) * s + ry * math.sin(u) * c)
           for u in (i / n * math.tau for i in range(n))]
    cv.polygon(pts, fill=tuple(col) + (int(a),))


def ball(cv: Canvas, x, y, rx, ry, col, rot=0.0, a=255, hi=True):
    """Soft-shaded round form: dark rim, lit body offset to the light (top-left), specular."""
    ell(cv, x, y, rx, ry, mix(col, (20, 20, 30), 0.38), a, rot)
    ell(cv, x - rx * 0.07, y - ry * 0.08, rx * 0.9, ry * 0.9, col, a, rot)
    ell(cv, x - rx * 0.14, y - ry * 0.16, rx * 0.66, ry * 0.64, mix(col, (255, 255, 255), 0.12), int(a * 0.8), rot)
    if hi and rx > 6:
        ell(cv, x - rx * 0.36, y - ry * 0.42, rx * 0.22, ry * 0.14, mix(col, (255, 255, 255), 0.7), int(a * 0.75),
            rot - 0.5)


def limb(cv: Canvas, p1, p2, r, col):
    """Rounded capsule (arm/leg) with a darker underside."""
    for off, cc, rr in ((1.5, mix(col, (20, 20, 30), 0.35), r), (0, col, r * 0.82)):
        a, b = (p1[0], p1[1] + off), (p2[0], p2[1] + off)
        cv.line([a, b], fill=cc + (255,), width=rr * 2)
        cv.circle(a[0], a[1], rr, fill=cc + (255,))
        cv.circle(b[0], b[1], rr, fill=cc + (255,))


def eyes(cv: Canvas, x, y, d, r, mood="normal", look=(0.0, 0.0)):
    for sd in (-1, 1):
        ex = x + sd * d
        if mood == "squint":            # >_<  (sour!)
            w = r * 1.1
            cv.line([(ex - w, y - r * 0.6), (ex + w * 0.2 * sd, y), (ex - w, y + r * 0.6)] if sd < 0 else
                    [(ex + w, y - r * 0.6), (ex - w * 0.2, y), (ex + w, y + r * 0.6)], fill=(30, 24, 24, 255),
                    width=max(2, r * 0.35))
            continue
        if mood == "happy":
            cv.d.arc([(ex - r) * cv.ss, (y - r * 0.6) * cv.ss, (ex + r) * cv.ss, (y + r * 1.0) * cv.ss], 200, 340,
                     fill=(30, 24, 24, 255), width=max(2, int(r * 0.35 * cv.ss)))
            continue
        k = 1.25 if mood == "wide" else 1.0
        ell(cv, ex, y, r * 0.82 * k, r * k, WHITE)
        ell(cv, ex + look[0] * r * 0.3, y + look[1] * r * 0.3 + r * 0.1, r * 0.52, r * 0.62, (28, 24, 26))
        ell(cv, ex + look[0] * r * 0.3 - r * 0.18, y - r * 0.18, r * 0.18, r * 0.18, (255, 255, 255))
        if mood == "angry":
            cv.line([(ex - r * 1.1 * sd, y - r * 1.5), (ex + r * 0.9 * sd, y - r * 0.9)], fill=(30, 20, 20, 255),
                    width=max(2, r * 0.45))


def mouth(cv: Canvas, x, y, w, kind="smile"):
    k = cv.ss
    if kind == "smile":
        cv.d.arc([(x - w) * k, (y - w * 0.8) * k, (x + w) * k, (y + w * 0.8) * k], 20, 160, fill=(120, 40, 40, 255),
                 width=max(2, int(w * 0.25 * k)))
    elif kind == "open":
        ell(cv, x, y + w * 0.2, w * 0.7, w * 0.75, (120, 30, 40))
        ell(cv, x, y + w * 0.55, w * 0.45, w * 0.3, (230, 110, 120))
    elif kind == "roar":
        ell(cv, x, y, w * 1.1, w * 0.85, (90, 20, 26))
        for sd in (-1, 1):
            cv.polygon([(x + sd * w * 0.7, y - w * 0.8), (x + sd * w * 0.45, y - w * 0.8), (x + sd * w * 0.58, y - w * 0.2)],
                       fill=(250, 246, 230, 255))
    elif kind == "wobbly":
        pts = [(x - w + i * w / 5, y + math.sin(i * 2.3) * w * 0.18) for i in range(11)]
        cv.line(pts, fill=(90, 24, 30, 255), width=max(2, w * 0.2))
    else:
        cv.line([(x - w * 0.6, y), (x + w * 0.6, y)], fill=(120, 40, 40, 255), width=max(2, w * 0.2))


@lru_cache(maxsize=1)
def _peel_dots(n=90, seed=3):
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        u, v = rnd.uniform(-1, 1), rnd.uniform(-1, 1)
        if u * u + v * v < 0.86:
            out.append((u, v, rnd.uniform(0.02, 0.04)))
    return tuple(out)


def sudachi(cv: Canvas, x, y, r, t=0.0, glow=0.0, leaf=True, rot=0.0, crack=0.0):
    """A sudachi: bright natural green, dimpled peel, stem and a leaf, glossy highlight."""
    if glow > 0:
        cv.glow(lambda d, k: d.ellipse([(x - r * 1.25) * k, (y - r * 1.2) * k, (x + r * 1.25) * k, (y + r * 1.2) * k],
                                       fill=GLOW + (255,)), radius=r * 0.5, strength=glow)
    ball(cv, x, y, r, r * 0.93, SUDACHI, rot)
    if r > 22:
        for u, v, s in _peel_dots():
            ell(cv, x + u * r * 0.95, y + v * r * 0.9, r * s, r * s, SUDACHI_D, 110)
        ell(cv, x - r * 0.36, y - r * 0.42, r * 0.24, r * 0.14, (236, 255, 220), 200, rot - 0.5)
        ell(cv, x - r * 0.2, y - r * 0.55, r * 0.07, r * 0.05, (255, 255, 255), 230)
    if r > 8:
        cv.line([(x, y - r * 0.88), (x + r * 0.05, y - r * 1.05)], fill=(90, 80, 40, 255), width=max(2, r * 0.06))
        if leaf:
            ell(cv, x + r * 0.28, y - r * 1.02, r * 0.32, r * 0.11, (40, 110, 36), rot=-0.35)
            cv.line([(x + r * 0.02, y - r * 1.0), (x + r * 0.55, y - r * 1.08)], fill=(70, 150, 60, 200), width=max(1, r * 0.02))
    if crack > 0:   # glowing cracks before it splits
        rnd = random.Random(7)
        for j in range(4):
            px, py = x + rnd.uniform(-0.2, 0.2) * r, y - r * 0.85
            pts = [(px, py)]
            for i in range(7):
                px += rnd.uniform(-0.18, 0.18) * r
                py += r * 0.25 * crack
                pts.append((px, py))
            cv.glow(lambda d, k, pts=pts: d.line([(a * k, b * k) for a, b in pts], fill=GLOW + (255,), width=int(8 * k)),
                    radius=12, strength=crack)
            cv.line(pts, fill=(240, 255, 210, 255), width=max(2, r * 0.03))


def sudachi_half(cv: Canvas, x, y, r, side, open_=0.0):
    """Half of a split sudachi seen from the cut: peel rim, pale flesh with segments."""
    ox = x + side * r * 0.9 * open_
    rot = side * 0.5 * open_
    ell(cv, ox, y, r * 0.55, r * 0.93, SUDACHI, rot=rot)
    ell(cv, ox - side * r * 0.08, y, r * 0.45, r * 0.85, FLESH, rot=rot)
    for i in range(8):
        a = i / 8 * math.tau
        cv.line([(ox - side * r * 0.08, y), (ox - side * r * 0.08 + math.cos(a) * r * 0.4 * math.cos(rot), y + math.sin(a) * r * 0.8)],
                fill=(200, 220, 120, 255), width=max(1, r * 0.02))


# ---------------------------------------------------------------- characters (feet at x, y; s = height px)
def taro(cv: Canvas, x, y, s, t=0.0, pose="stand", face="smile", giant=0.0, hold=False):
    """すだち太郎: green haori with a white sudachi-slice crest, cream hakama, white hachimaki with a sudachi,
    black hair with a top-knot. giant>0 adds the sudachi-peel armour and green aura (the awakened form)."""
    u = s / 100
    bob = math.sin(t * 6) * u * 1.2 if pose in ("walk", "jump") else 0
    y = y - bob
    if giant > 0:
        cv.glow(lambda d, k: d.ellipse([(x - 60 * u) * k, (y - 110 * u) * k, (x + 60 * u) * k, (y + 4 * u) * k],
                                       fill=GLOW + (255,)), radius=30 * u, strength=0.6 * giant)
    for sd in (-1, 1):                                                       # legs + zori
        step = math.sin(t * 8 + (0 if sd > 0 else math.pi)) * 4 * u if pose == "walk" else 0
        limb(cv, (x + sd * 9 * u, y - 26 * u), (x + sd * 10 * u + step, y - 4 * u), 6 * u,
             mix(HAKAMA, SUDACHI, 0.6 * giant))
        ell(cv, x + sd * 10 * u + step, y - 2 * u, 9 * u, 4 * u, (110, 70, 40))
    ball(cv, x, y - 34 * u, 23 * u, 16 * u, mix(HAKAMA, SUDACHI_D, 0.5 * giant))  # hakama
    ball(cv, x, y - 54 * u, 24 * u, 17 * u, mix(HAORI, SUDACHI, 0.4 * giant))     # haori
    if giant > 0:
        for uu, vv, ss in _peel_dots()[:40]:
            ell(cv, x + uu * 22 * u, y - 54 * u + vv * 15 * u, ss * 30 * u, ss * 30 * u, SUDACHI_D, int(140 * giant))
    ell(cv, x, y - 55 * u, 7 * u, 7 * u, WHITE)                                   # crest: sudachi slice
    ell(cv, x, y - 55 * u, 5 * u, 5 * u, FLESH)
    for i in range(6):
        a = i / 6 * math.tau
        cv.line([(x, y - 55 * u), (x + math.cos(a) * 5 * u, y - 55 * u + math.sin(a) * 5 * u)], fill=(170, 200, 90, 255),
                width=max(1, u * 0.6))
    arms = {"stand": ((-0.6, 0.9), (0.6, 0.9)), "walk": ((-0.4, 1.0), (0.4, 1.0)), "hold_up": ((-0.6, 0.9), (0.45, -1.7)),
            "squeeze": ((-0.55, 0.15), (0.55, 0.15)), "give": ((-0.6, 0.9), (0.95, 0.15)), "jump": ((-0.9, -0.7), (0.9, -0.7))}[pose]
    hands = []
    for sd, (ax, ay) in zip((-1, 1), arms):
        sh = (x + sd * 19 * u, y - 62 * u)
        hd = (sh[0] + ax * 26 * u, sh[1] + ay * 24 * u)
        limb(cv, sh, hd, 6 * u, mix(HAORI, SUDACHI, 0.4 * giant))
        ball(cv, hd[0], hd[1], 5.5 * u, 5.5 * u, SKIN, hi=False)
        hands.append(hd)
    hy = y - 88 * u                                                          # head
    ball(cv, x, hy, 22 * u, 21 * u, SKIN)
    ell(cv, x, hy - 12 * u, 22.5 * u, 11 * u, HAIR)
    ball(cv, x + 2 * u, hy - 25 * u, 6 * u, 6 * u, HAIR)
    cv.line([(x - 22 * u, hy - 9 * u), (x + 22 * u, hy - 9 * u)], fill=WHITE + (255,), width=4.5 * u)
    sudachi(cv, x, hy - 9 * u, 4.2 * u, leaf=False)
    eyes(cv, x, hy + 2 * u, 8 * u, 4 * u, "angry" if face == "fierce" else ("wide" if face == "wow" else "normal"))
    for sd in (-1, 1):
        ell(cv, x + sd * 13 * u, hy + 9 * u, 4 * u, 2.4 * u, (255, 150, 150), 140)
    mouth(cv, x, hy + 11 * u, 5 * u, "open" if face in ("wow", "fierce") else ("flat" if face == "flat" else "smile"))
    return hands


def granny(cv: Canvas, x, y, s, t=0.0, face="normal", knife=False):
    u = s / 100
    ball(cv, x, y - 32 * u, 26 * u, 32 * u, (120, 90, 140))                   # kimono
    ell(cv, x, y - 40 * u, 26 * u, 4 * u, (200, 170, 90))                    # obi
    hy = y - 74 * u
    ball(cv, x, hy, 18 * u, 17 * u, SKIN)
    ell(cv, x, hy - 10 * u, 18 * u, 9 * u, (200, 200, 205))
    ball(cv, x, hy - 22 * u, 8 * u, 7 * u, (200, 200, 205))
    eyes(cv, x, hy + 1 * u, 6.5 * u, 3 * u, "wide" if face == "wow" else "happy")
    mouth(cv, x, hy + 9 * u, 4 * u, "open" if face == "wow" else "smile")
    for sd in (-1, 1):
        limb(cv, (x + sd * 20 * u, y - 52 * u), (x + sd * 30 * u, y - 38 * u if not (knife and sd > 0) else y - 66 * u),
             5 * u, (120, 90, 140))
    if knife:
        kx, ky = x + 30 * u, y - 66 * u
        cv.polygon([(kx, ky - 2 * u), (kx + 26 * u, ky - 8 * u), (kx + 28 * u, ky - 3 * u), (kx, ky + 2 * u)],
                   fill=(220, 225, 232, 255))
        cv.rect(kx - 9 * u, ky - 2 * u, kx, ky + 2 * u, fill=(90, 60, 40, 255))


def dog(cv: Canvas, x, y, s, t=0.0, face="smile"):
    u = s / 100
    wag = math.sin(t * 14) * 0.5
    limb(cv, (x + 32 * u, y - 46 * u), (x + 44 * u, y - 62 * u + wag * 6 * u), 5 * u, DOG)
    for dx in (-24, -10, 14, 28):
        limb(cv, (x + dx * u, y - 30 * u), (x + dx * u, y - 4 * u), 6 * u, DOG)
    ball(cv, x + 4 * u, y - 40 * u, 38 * u, 20 * u, DOG)
    ell(cv, x - 4 * u, y - 34 * u, 18 * u, 10 * u, WHITE, 200)
    hx, hy = x - 30 * u, y - 66 * u
    ball(cv, hx, hy, 22 * u, 19 * u, DOG)
    for sd in (-1, 1):
        cv.polygon([(hx + sd * 6 * u, hy - 14 * u), (hx + sd * 18 * u, hy - 30 * u), (hx + sd * 20 * u, hy - 10 * u)],
                   fill=mix(DOG, (150, 100, 60), 0.4) + (255,))
    ell(cv, hx - 6 * u, hy + 8 * u, 12 * u, 8 * u, WHITE)
    ell(cv, hx - 12 * u, hy + 4 * u, 4 * u, 3 * u, (30, 26, 26))
    eyes(cv, hx + 2 * u, hy - 4 * u, 7 * u, 3.2 * u, "happy" if face == "happy" else "normal", (-0.5, 0))
    mouth(cv, hx - 6 * u, hy + 12 * u, 4 * u, "smile")


def monkey(cv: Canvas, x, y, s, t=0.0, face="smile"):
    u = s / 100
    for sd in (-1, 1):
        limb(cv, (x + sd * 10 * u, y - 26 * u), (x + sd * 14 * u, y - 4 * u), 6 * u, MONKEY)
        limb(cv, (x + sd * 20 * u, y - 56 * u), (x + sd * 34 * u, y - 30 * u), 5.5 * u, MONKEY)
    limb(cv, (x + 18 * u, y - 24 * u), (x + 40 * u, y - 40 * u + math.sin(t * 3) * 6 * u), 3 * u, MONKEY)
    ball(cv, x, y - 44 * u, 22 * u, 26 * u, MONKEY)
    ell(cv, x, y - 40 * u, 13 * u, 16 * u, MFACE, 220)
    hy = y - 82 * u
    ball(cv, x, hy, 22 * u, 20 * u, MONKEY)
    for sd in (-1, 1):
        ball(cv, x + sd * 22 * u, hy, 7 * u, 8 * u, MFACE, hi=False)
    ell(cv, x, hy + 3 * u, 15 * u, 13 * u, MFACE)
    eyes(cv, x, hy - 1 * u, 6 * u, 3.2 * u, "happy" if face == "happy" else "normal")
    mouth(cv, x, hy + 8 * u, 4 * u, "smile")


def kiji(cv: Canvas, x, y, s, t=0.0, wings=0.0):
    """Pheasant: green body, red face, long striped tail. wings 0..1 = spread."""
    u = s / 100
    flap = math.sin(t * 9) * 0.4 * wings
    for sd in (-1, 1):
        w = 40 * u * (0.5 + wings)
        cv.polygon([(x + sd * 8 * u, y - 52 * u), (x + sd * (8 * u + w), y - 52 * u - w * (0.6 + flap)),
                    (x + sd * (8 * u + w * 0.9), y - 40 * u)], fill=mix(KIJI, (140, 110, 60), 0.5) + (255,))
    cv.polygon([(x + 10 * u, y - 36 * u), (x + 70 * u, y - 18 * u), (x + 66 * u, y - 12 * u), (x + 8 * u, y - 30 * u)],
               fill=(150, 120, 70, 255))
    for i in range(5):
        cv.line([(x + (20 + i * 10) * u, y - (33 - i * 3) * u), (x + (22 + i * 10) * u, y - (26 - i * 3) * u)],
                fill=(80, 60, 40, 255), width=max(1, 1.5 * u))
    for sd in (-1, 1):
        cv.line([(x + sd * 4 * u, y - 22 * u), (x + sd * 5 * u, y)], fill=(190, 150, 80, 255), width=max(2, 2 * u))
    ball(cv, x, y - 40 * u, 18 * u, 20 * u, KIJI)
    hx, hy = x - 6 * u, y - 66 * u
    ball(cv, hx, hy, 11 * u, 12 * u, KIJI)
    ell(cv, hx - 2 * u, hy - 1 * u, 8 * u, 6 * u, KIJI_RED)
    cv.polygon([(hx - 10 * u, hy + 1 * u), (hx - 18 * u, hy + 4 * u), (hx - 10 * u, hy + 5 * u)], fill=(240, 210, 120, 255))
    eyes(cv, hx - 3 * u, hy - 1 * u, 0.1, 2.4 * u)


def oni(cv: Canvas, x, y, s, t=0.0, face="angry", arms="down"):
    """Red oni: muscular, two horns, wild hair, tiger-striped yellow cloth. face: angry / roar / cry."""
    u = s / 100
    for sd in (-1, 1):
        limb(cv, (x + sd * 14 * u, y - 30 * u), (x + sd * 17 * u, y - 4 * u), 9 * u, ONI)
        ell(cv, x + sd * 18 * u, y - 2 * u, 12 * u, 5 * u, ONI_D)
    ball(cv, x, y - 34 * u, 26 * u, 14 * u, GOLD)
    for i in range(5):
        cv.line([(x - 18 * u + i * 9 * u, y - 44 * u), (x - 14 * u + i * 9 * u, y - 24 * u)], fill=(60, 40, 20, 220),
                width=max(2, 3 * u))
    ball(cv, x, y - 62 * u, 32 * u, 24 * u, ONI)
    ell(cv, x, y - 56 * u, 18 * u, 12 * u, mix(ONI, (255, 220, 200), 0.18), 200)
    pose = {"down": ((-0.5, 1.0), (0.5, 1.0)), "up": ((-0.8, -1.0), (0.8, -1.0)), "charge": ((-0.2, 0.6), (0.9, 0.0)),
            "take": ((-0.5, 1.0), (-0.95, 0.1))}[arms]
    for sd, (ax, ay) in zip((-1, 1), pose):
        sh = (x + sd * 30 * u, y - 72 * u)
        hd = (sh[0] + ax * 28 * u, sh[1] + ay * 26 * u)
        ball(cv, sh[0], sh[1], 12 * u, 12 * u, ONI, hi=False)
        limb(cv, sh, hd, 8.5 * u, ONI)
        ball(cv, hd[0], hd[1], 8 * u, 8 * u, ONI_D, hi=False)
    hy = y - 102 * u
    ball(cv, x, hy, 22 * u, 21 * u, ONI)
    for i in range(9):                                                       # wild hair
        a = math.pi + i / 8 * math.pi
        ball(cv, x + math.cos(a) * 20 * u, hy - 8 * u + math.sin(a) * 15 * u, 8 * u, 7 * u, (40, 30, 30), hi=False)
    for sd in (-1, 1):
        cv.polygon([(x + sd * 9 * u, hy - 18 * u), (x + sd * 15 * u, hy - 40 * u), (x + sd * 19 * u, hy - 16 * u)],
                   fill=(250, 240, 210, 255))
    if face == "cry":
        eyes(cv, x, hy + 1 * u, 8 * u, 4 * u, "squint")
        for sd in (-1, 1):                                                   # comic tear streams
            for k in range(3):
                ph = (t * 2.5 + k / 3) % 1
                ell(cv, x + sd * (12 + 14 * ph) * u, hy + (6 + 40 * ph) * u, 3 * u, 4 * u, (150, 210, 255), int(230 * (1 - ph)))
            cv.line([(x + sd * 10 * u, hy + 5 * u), (x + sd * 13 * u, hy + 20 * u)], fill=(150, 210, 255, 230), width=3 * u)
        mouth(cv, x, hy + 12 * u, 6 * u, "wobbly")
    else:
        eyes(cv, x, hy - 1 * u, 8 * u, 4 * u, "angry")
        mouth(cv, x, hy + 11 * u, 7 * u, "roar" if face == "roar" else "flat")


# ---------------------------------------------------------------- environments
def hills(cv: Canvas, base, cols, par=0.0, t=0.0):
    for i, col in enumerate(cols):
        off = par * (i + 1) * 0.4
        pts = [(x, base - 120 - i * 40 + math.sin(x * 0.006 + i * 2 + off * 0.01) * (60 - i * 10)) for x in range(-40, W + 60, 40)]
        cv.polygon(pts + [(W + 60, H), (-40, H)], fill=col + (255,))


def river(cv: Canvas, top, t, cam_low=0.0):
    cv.img.paste(gradient(cv.ss, (88, 160, 170), (40, 100, 120)).crop((0, 0, W * cv.ss, int((H - top) * cv.ss))),
                 (0, int(top * cv.ss)))
    rnd = random.Random(2)
    for i in range(70):
        yy = top + (rnd.random() ** 2) * (H - top)
        xx = (rnd.uniform(-100, W) + t * 60 * (1 + (yy - top) / 300)) % (W + 200) - 100
        L = 20 + (yy - top) * 0.25
        cv.line([(xx, yy), (xx + L, yy)], fill=(220, 240, 240, 110), width=max(1, (yy - top) * 0.012))


def bokeh(cv: Canvas, t, col=(190, 240, 170)):
    rnd = random.Random(5)
    for i in range(26):
        x = rnd.uniform(0, W)
        y = (rnd.uniform(0, H) - t * 20 * rnd.uniform(0.5, 1.5)) % H
        r = rnd.uniform(20, 90)
        cv.circle(x, y, r, fill=mix(col, (255, 255, 255), rnd.random() * 0.5) + (int(rnd.uniform(30, 80)),))


def particles(cv: Canvas, t, origin, n=60, speed=900, col=GLOW, seed=1, life=1.2, g=600, size=8):
    if t < 0 or t > life:
        return
    rnd = random.Random(seed)
    for i in range(n):
        a = rnd.uniform(0, math.tau)
        v = rnd.uniform(0.3, 1.0) * speed
        x = origin[0] + math.cos(a) * v * t
        y = origin[1] + math.sin(a) * v * t + 0.5 * g * t * t
        cv.circle(x, y, size * rnd.uniform(0.5, 1.2) * (1 - t / life * 0.5), fill=col + (int(220 * (1 - t / life)),))


def light_rays(cv: Canvas, cx, cy, t, strength=1.0, n=14, length=1400, col=GLOW):
    for i in range(n):
        a = i / n * math.tau + t * 0.3
        w = 0.06
        cv.polygon([(cx, cy), (cx + math.cos(a - w) * length, cy + math.sin(a - w) * length),
                    (cx + math.cos(a + w) * length, cy + math.sin(a + w) * length)], fill=col + (int(70 * strength),))


def cam_shake(t, impacts, base=0.0):
    amp = base + sum(s * math.exp(-(t - ti) * 6) for ti, s in impacts if t >= ti)
    return math.sin(t * 41) * amp, math.cos(t * 37) * amp


def finish_cam(cv: Canvas, zoom=1.0, cx=W / 2, cy=H / 2, rot=0.0):
    """Post camera: zoom about (cx, cy) and roll the whole frame (for dolly-ins and dutch tilts)."""
    zoom = max(1.0, zoom, 1.0 + abs(rot) * 1.9)          # never reveal the frame edge (no black borders)
    if zoom == 1.0 and rot == 0.0:
        return
    k = cv.ss
    im = cv.img
    if rot:
        im = im.rotate(math.degrees(rot), resample=Image.BILINEAR, center=(W * k / 2, H * k / 2))
    if zoom != 1.0:
        w, h = W * k / zoom, H * k / zoom
        x0 = clamp(cx * k - w / 2, 0, W * k - w) if not rot else clamp(cx * k - w / 2, (W * k - w) * 0.25, (W * k - w) * 0.75)
        y0 = clamp(cy * k - h / 2, 0, H * k - h) if not rot else clamp(cy * k - h / 2, (H * k - h) * 0.25, (H * k - h) * 0.75)
        im = im.transform(cv.img.size, Image.EXTENT, (x0, y0, x0 + w, y0 + h), Image.BILINEAR)
    cv.img = im
    from PIL import ImageDraw
    cv.d = ImageDraw.Draw(cv.img)


def clip_bg(cv: Canvas, P, t) -> bool:
    """Paste the pre-rendered 3D frame for this scene time (Blender hero shot). False -> draw the 2.5D version."""
    if not P.get("clip"):
        return False
    from .. import clips
    from .engine import RUNTIME
    im = clips.frame(RUNTIME.get("post_dir"), P["clip"], t)
    if im is None:
        return False
    if im.size != cv.img.size:
        im = im.resize(cv.img.size, Image.LANCZOS)
    cv.img.paste(im, (0, 0))
    return True


def bars(cv: Canvas):
    cv.rect(0, 0, W, 130, fill=(12, 12, 14, 220))
    cv.rect(0, H - 150, W, H, fill=(12, 12, 14, 220))


def slowmo(t, a, b, r):
    if t <= a:
        return t
    if t <= b:
        return a + (t - a) * r
    return a + (b - a) * r + (t - b)


# ---------------------------------------------------------------- S1 river
@scene("sd_river")
def sd_river(cv: Canvas, t, dur, P, ctx: SceneCtx):
    split = P.get("granny_at", 3.1)
    if t < split and clip_bg(cv, P, t):   # real 3D shot (Blender) when available
        pass
    elif t < split:                    # water-level tracking of the giant sudachi (2.5D fallback)
        q = t / split
        sky(cv, ((150, 200, 236), (236, 240, 226)))
        hills(cv, 820, [(120, 160, 120), (86, 132, 92), (64, 110, 70)], par=t * 80)
        river(cv, 760, t)
        bob = math.sin(t * 2.4) * 10
        x = lerp(760, 520, ease_in_out(q))
        r = lerp(300, 380, q)
        ell(cv, x + 20, 1020 + r * 0.4, r * 1.1, 40, (20, 60, 70), 120)        # reflection/shadow
        sudachi(cv, x, 1000 + bob - r * 0.5, r, t)
        for i in range(10):                                                  # spray at the waterline
            ph = (t * 1.3 + i * 0.1) % 1
            cv.circle(x - r * 0.9 + i * r * 0.2, 1000 + bob + r * 0.35 - ph * 40, 6 * (1 - ph), fill=(240, 255, 255, int(200 * (1 - ph))))
        zoom = 1.0 + 0.05 * q
        finish_cam(cv, zoom, 540, 1000)
    else:                              # granny on the bank, surprised
        tb = t - split
        sky(cv, ((150, 200, 236), (236, 240, 226)))
        hills(cv, 760, [(120, 160, 120), (86, 132, 92)])
        river(cv, 980, t)
        cv.polygon([(0, 980), (W, 940), (W, 1040), (0, 1100)], fill=(150, 170, 110, 255))
        sudachi(cv, 860 - tb * 40, 1060, 260, t)
        granny(cv, 300, 1080, 420, t, face="wow")
        if tb < 0.6:
            cv.text(330, 560, "！", 150 * ease_out_back(clamp(tb / 0.3)), C["accent"], stroke=6)
        finish_cam(cv, 1.0 + 0.12 * ease_out(tb / max(0.1, dur - split)), 300, 760)
    bars(cv)


# ---------------------------------------------------------------- S2 birth
@scene("sd_birth")
def sd_birth(cv: Canvas, t, dur, P, ctx: SceneCtx):
    split_at = P.get("split_at", 3.2)
    st = slowmo(t, split_at - 0.1, split_at + 0.8, 0.35)
    sx, sy = cam_shake(t, [(1.4, 6), (split_at, 22)], base=3 * clamp((t - 1.2) / 1.5) if t < split_at else 0)
    cv.img.paste(gradient(cv.ss, (120, 90, 70), (70, 50, 40)), (0, 0))      # wooden house interior
    for i in range(9):
        cv.rect(i * 130 + sx, 200 + sy, i * 130 + 90 + sx, 900 + sy, fill=(232, 222, 196, 255))   # shoji panes
        for j in range(5):
            cv.line([(i * 130 + sx, 200 + j * 140 + sy), (i * 130 + 90 + sx, 200 + j * 140 + sy)], fill=(150, 110, 80, 255), width=4)
    cv.rect(0, 1100 + sy, W, H, fill=(150, 108, 70, 255))
    for j in range(8):
        cv.line([(0, 1100 + j * 90 + sy), (W, 1100 + j * 90 + sy)], fill=(120, 84, 54, 255), width=3)
    cx, cy, r = 560 + sx, 900 + sy, 330
    if st < split_at:
        crack = clamp((t - 1.6) / 1.4)
        granny(cv, 170 + sx, 1260 + sy, 380, t, face="wow" if t > 1.4 else "normal", knife=True)
        sudachi(cv, cx, cy, r, t, glow=crack * 0.8, crack=crack)
        if crack > 0.3:
            light_rays(cv, cx, cy - r * 0.6, t, strength=crack)
        z = 1.0 + 0.25 * ease_in_out(t / split_at)
        finish_cam(cv, z, cx, cy - 60)
    else:
        q = ease_out(clamp((st - split_at) / 0.9))
        light_rays(cv, cx, cy, t, strength=1 - q * 0.5, length=1600)
        cv.glow(lambda d, k: d.ellipse([(cx - 300) * k, (cy - 300) * k, (cx + 300) * k, (cy + 300) * k], fill=GLOW + (255,)),
                radius=120, strength=1 - q * 0.4)
        sudachi_half(cv, cx, cy, r, -1, q)
        sudachi_half(cv, cx, cy, r, 1, q)
        particles(cv, st - split_at, (cx, cy), n=70, speed=900, seed=3, life=1.6)
        jump = ease_out(clamp((st - split_at - 0.15) / 0.7))
        ty = lerp(cy + 120, 1240, jump) - math.sin(jump * math.pi) * 380
        taro(cv, cx, ty, lerp(200, 560, jump), t, pose="jump", face="wow")
        if st - split_at < 0.15:
            cv.rect(0, 0, W, H, fill=(240, 255, 220, int(255 * (1 - (st - split_at) / 0.15))))
        finish_cam(cv, lerp(1.25, 1.0, jump), cx, 900)
    bars(cv)


# ---------------------------------------------------------------- S3 companions + growth
@scene("sd_companions")
def sd_companions(cv: Canvas, t, dur, P, ctx: SceneCtx):
    grow_at = P.get("grow_at", 2.6)
    sky(cv, ((140, 196, 236), (240, 238, 216)))
    if t < grow_at:                    # quick meetings: each gets a sudachi instead of kibidango
        hills(cv, 900, [(130, 170, 110), (96, 140, 90)], par=t * 200)
        cv.rect(0, 1150, W, H, fill=(196, 176, 120, 255))
        k = int(t / (grow_at / 3))
        q = (t % (grow_at / 3)) / (grow_at / 3)
        taro(cv, 330, 1400, 520, t, pose="give", face="smile")
        sx = 330 + 95 * 5.2 * 0.95
        x = lerp(1160, 790, ease_out(q * 2))
        [dog, monkey, kiji][min(k, 2)](cv, x, 1400, 380, t)
        fly = clamp((q - 0.25) * 3)
        sudachi(cv, lerp(sx - 120, x - 60, fly), lerp(1150, 1100, fly) - math.sin(fly * math.pi) * 120, 46, t)
        finish_cam(cv, 1.05 + 0.04 * math.sin(t * 3), 560, 1200)
    else:                              # the three grow huge (looking up), then pull up to the sky
        tb = t - grow_at
        g = ease_in_out(clamp(tb / 1.6))
        hills(cv, 1300, [(130, 170, 110), (96, 140, 90)])
        cv.rect(0, 1600, W, H, fill=(196, 176, 120, 255))
        for i, (fn, x, sc0, sc1) in enumerate(((dog, 260, 160, 760), (monkey, 760, 160, 1250), (kiji, 520, 120, 1500))):
            s = lerp(sc0, sc1, ease_in_out(clamp((tb - i * 0.25) / 1.6)))
            yy = 1620 if fn is not kiji else lerp(1620, 1180, g)
            if fn is kiji:
                fn(cv, x, yy, s, t, wings=g)
            else:
                fn(cv, x, yy, s, t, face="happy")
        cv.glow(lambda d, k: d.rectangle([0, 1450 * k, W * k, 1700 * k], fill=GLOW + (255,)), radius=80, strength=0.5 * (1 - g))
        taro(cv, 540, 1640, 150, t, pose="jump", face="wow")
        sx, sy = cam_shake(tb, [(0.2, 8), (0.6, 8), (1.0, 10)])
        finish_cam(cv, lerp(1.0, 0.82, g), 540 + sx, lerp(1300, 1000, g) + sy)
    bars(cv)


# ---------------------------------------------------------------- S4 Onigashima
def onigashima(cv: Canvas, t, sy=0.0):
    sky(cv, ((40, 40, 56), (110, 90, 100)))
    rnd = random.Random(9)
    for i in range(10):                                                      # rolling dark clouds
        x = (rnd.uniform(0, W) + t * 30 * (1 + i % 3)) % (W + 400) - 200
        cv.glow(lambda d, k, x=x, i=i: d.ellipse([(x - 260) * k, (120 + i * 40) * k, (x + 260) * k, (300 + i * 40) * k],
                                                 fill=(70, 66, 80, 255)), radius=40, strength=0.9)
    cv.polygon([(0, 1150 + sy), (160, 700 + sy), (330, 860 + sy), (520, 560 + sy), (720, 820 + sy), (900, 640 + sy),
                (1080, 900 + sy), (1080, 1300 + sy), (0, 1300 + sy)], fill=(56, 50, 56, 255))
    cv.rect(0, 1250 + sy, W, H, fill=(80, 70, 66, 255))


@scene("sd_oni")
def sd_oni(cv: Canvas, t, dur, P, ctx: SceneCtx):
    stomps = [1.0, 2.0, 3.0]
    sx, sy = cam_shake(t, [(s, 26) for s in stomps])
    onigashima(cv, t, sy)
    rise = ease_out(clamp(t / 1.2))
    oy = lerp(2300, 1640, rise) + sy
    face = "roar" if t > ctx.line_start(0, 2.4) - 0.1 else "angry"
    oni(cv, 540 + sx, oy, 1080, t, face=face, arms="up" if face == "roar" else "down")
    for s in stomps:
        particles(cv, t - s, (540 + sx, 1700 + sy), n=40, speed=700, col=(150, 130, 110), seed=int(s * 10), life=1.4, g=900, size=12)
    for i, (fn, x) in enumerate(((taro, 300), (dog, 620), (monkey, 860))):    # small heroes looking up (foreground)
        if fn is taro:
            fn(cv, x + sx * 1.5, 1820 + sy * 1.5, 260, t, face="fierce")
        else:
            fn(cv, x + sx * 1.5, 1830 + sy * 1.5, 200, t)
    finish_cam(cv, 1.0 + 0.06 * ease_in_out(t / dur), 540, 1100, rot=0.025 * math.sin(t * 0.8))
    bars(cv)


# ---------------------------------------------------------------- S5 awakening
@scene("sd_awaken")
def sd_awaken(cv: Canvas, t, dur, P, ctx: SceneCtx):
    raise_at, grow_at = P.get("raise_at", 1.2), P.get("grow_at", 2.4)
    dark = clamp((t - raise_at) / 0.6)
    onigashima(cv, t)
    cv.rect(0, 0, W, H, fill=(10, 14, 20, int(150 * dark)))
    g = ease_in_out(clamp((t - grow_at) / 2.4))
    sx, sy = cam_shake(t, [(raise_at + 0.5, 10), (grow_at, 16), (grow_at + 2.4, 20)], base=6 * g * (1 - g) * 4)
    if t < raise_at:   # the oni charges (tracking): big, blurred, close
        q = t / raise_at
        oni(cv, lerp(900, 640, q) + sx, 2300 + sy, 1600, t, face="roar", arms="charge")
        for i in range(12):
            yy = (i * 157 + t * 2400) % H
            cv.line([(i * 90, yy), (i * 90 - 30, yy + 140)], fill=(255, 255, 255, 60), width=4)
    else:
        for i in range(7):   # cracks with green energy erupting
            ang = -math.pi / 2 + (i - 3) * 0.35
            L = 900 * clamp((t - raise_at - 0.3) / 0.8)
            pts = [(540 + sx, 1650 + sy)]
            for j in range(6):
                d = L * (j + 1) / 6
                pts.append((540 + math.cos(ang + (j % 2 - 0.5) * 0.15) * d * 1.1 + sx, 1650 + abs(math.sin(ang)) * d * 0.25 + sy))
            cv.glow(lambda dd, k, pts=pts: dd.line([(a * k, b * k) for a, b in pts], fill=GLOW + (255,), width=int(14 * k)),
                    radius=24, strength=dark)
            cv.line(pts, fill=(230, 255, 210, 255), width=5)
        for i in range(30):   # rising energy motes
            ph = (t * 0.8 + i / 30) % 1
            cv.circle(80 + (i * 37) % 920 + sx, 1700 - ph * 1500 + sy, 6 + 8 * (1 - ph), fill=GLOW + (int(200 * (1 - ph) * dark),))
        s = lerp(520, 1420, g)
        light_rays(cv, 540 + sx, 1700 - s * 0.5 + sy, t, strength=dark * (0.5 + g))
        hands = taro(cv, 540 + sx, 1720 + sy + g * 230, s, t, pose="hold_up", face="fierce", giant=g)
        rs = 16 * s / 100
        sudachi(cv, hands[1][0], hands[1][1] - rs * 0.9, rs, t, glow=0.8)
        if abs(t - grow_at) < 0.15:
            cv.rect(0, 0, W, H, fill=(220, 255, 200, int(255 * (1 - abs(t - grow_at) / 0.15))))
    finish_cam(cv, 1.0 + 0.1 * math.sin(clamp(t / dur) * math.pi), 540 + math.sin(t * 0.7) * 30, 1200, rot=0.04 * math.sin(t * 0.9))
    bars(cv)


# ---------------------------------------------------------------- S6 final blow
@scene("sd_final")
def sd_final(cv: Canvas, t, dur, P, ctx: SceneCtx):
    squeeze, fire, boom = P.get("squeeze_at", 0.4), P.get("fire_at", 1.6), P.get("boom_at", 3.0)
    st = slowmo(t, boom - 0.05, boom + 1.2, 0.35)
    sx, sy = cam_shake(st, [(fire, 18), (boom, 40)])
    if st < fire:                       # close on the giant hands squeezing a sudachi
        onigashima(cv, t)
        cv.rect(0, 0, W, H, fill=(10, 14, 20, 120))
        q = clamp((st - squeeze) / (fire - squeeze))
        r = 330 * (1 - 0.25 * q)
        sudachi(cv, 540 + sx, 1000 + sy, r, t, glow=0.4 + q)
        for sd in (-1, 1):
            ball(cv, 540 + sd * (r + 70 - q * 60) + sx, 1000 + sy, 150, 190, mix(HAORI, SUDACHI, 0.5))
            ball(cv, 540 + sd * (r + 10 - q * 60) + sx, 1000 + sy, 95, 120, SKIN)
        for i in range(int(40 * q)):    # juice spray
            a = random.Random(i).uniform(-math.pi, 0)
            d = (st * 600 + i * 37) % 500
            cv.circle(540 + math.cos(a) * d + sx, 1000 + math.sin(a) * d + sy, 10, fill=(220, 255, 170, 200))
        finish_cam(cv, 1.15 - 0.1 * q, 540, 1000)
    elif st < boom:                     # the juice beam (tracking along it) hits the oni
        q = (st - fire) / (boom - fire)
        onigashima(cv, t)
        oni(cv, 820 + sx, 1900 + sy, 1300, t, face="roar", arms="charge")
        x1 = lerp(0, 760, ease_in_out(q))
        beam = [(-100 + sx, 1300 + sy), (x1 + sx, 1050 + sy)]
        cv.glow(lambda d, k: d.line([(a * k, b * k) for a, b in beam], fill=GLOW + (255,), width=int(220 * k)), radius=90, strength=1.0)
        cv.line(beam, fill=(240, 255, 220, 255), width=110)
        for i in range(40):
            f = (i / 40 + st * 2) % 1
            px, py = lerp(beam[0][0], beam[1][0], f), lerp(beam[0][1], beam[1][1], f)
            cv.circle(px + math.sin(i) * 80, py + math.cos(i * 1.3) * 80, 12, fill=(220, 255, 170, 200))
        finish_cam(cv, 1.0, 540, 1100, rot=-0.05)
    else:                               # explosion, then pull back to the whole island
        tb = st - boom
        pull = ease_out(clamp(tb / 2.2))
        sky(cv, ((40, 40, 56), (110, 90, 100)))
        cv.rect(0, 1100 + sy, W, H, fill=(40, 80, 110, 255))                 # sea
        isl = [(160, 1110), (300, 900), (420, 980), (540, 820), (680, 960), (800, 880), (920, 1110)]
        cv.polygon([(x + sx, y + sy) for x, y in isl], fill=(56, 50, 56, 255))
        swell = math.sin(min(tb, 1.5) * 2) * 60 * math.exp(-tb)
        cv.polygon([(0, 1100 + sy - swell), (W, 1100 + sy - swell), (W, 1180 + sy), (0, 1180 + sy)], fill=(70, 120, 150, 255))
        R = 120 + tb * 520
        cv.glow(lambda d, k: d.ellipse([(540 - R) * k, (900 - R) * k, (540 + R) * k, (900 + R) * k], fill=(210, 255, 160, 255)),
                radius=R * 0.3, strength=max(0, 1.2 - tb * 0.7))
        cv.circle(540 + sx, 900 + sy, R * 0.55, fill=(240, 255, 220, int(230 * clamp(1 - tb / 2))))
        cv.circle(540 + sx, 900 + sy, R, outline=(255, 255, 255, int(200 * clamp(1 - tb / 1.5))), width=12)
        particles(cv, tb, (540 + sx, 900 + sy), n=90, speed=1100, col=(220, 255, 170), seed=11, life=2.4, g=500, size=10)
        for i in range(14):   # smoke
            a = i / 14 * math.tau
            d = 200 + tb * 220
            cv.glow(lambda dd, k, a=a, d=d: dd.ellipse([(540 + math.cos(a) * d - 130) * k, (900 + math.sin(a) * d * 0.5 - 90) * k,
                                                        (540 + math.cos(a) * d + 130) * k, (900 + math.sin(a) * d * 0.5 + 90) * k],
                                                       fill=(120, 130, 120, 255)), radius=50, strength=clamp(tb / 0.8) * 0.45)
        if tb < 0.2:
            cv.rect(0, 0, W, H, fill=(255, 255, 240, int(255 * (1 - tb / 0.2))))
        finish_cam(cv, lerp(2.2, 0.95, pull), 540, 950)
    bars(cv)


# ---------------------------------------------------------------- S7 the punchline
@scene("sd_ponzu")
def sd_ponzu(cv: Canvas, t, dur, P, ctx: SceneCtx):
    give_at = ctx.line_start(0, 1.0) + P.get("give_after", 1.8)
    sky(cv, ((120, 130, 150), (200, 190, 180)))
    cv.rect(0, 1250, W, H, fill=(110, 100, 92, 255))
    for i in range(8):   # lingering smoke clearing
        a = clamp(1 - t / 1.8)
        cv.glow(lambda d, k, i=i: d.ellipse([(i * 150 - 120) * k, (900 + (i % 3) * 120) * k, (i * 150 + 160) * k, (1150 + (i % 3) * 120) * k],
                                            fill=(200, 200, 196, 255)), radius=50, strength=a)
    oni(cv, 600, 1700, 1050, t, face="cry", arms="take" if t > give_at else "down")
    took = t > give_at + 0.4
    if t > give_at:   # taro's giant hand offering one sudachi (silently)
        q = ease_out(clamp((t - give_at) / 0.5))
        hx = lerp(1250, 420 if not took else 330, q)
        ball(cv, hx + 120, 1180, 120, 80, mix(HAORI, SUDACHI, 0.5))
        ball(cv, hx, 1180, 70, 60, SKIN)
        sudachi(cv, hx - 10 if not took else 330, 1110 if not took else 1060, 52, t)
    z = 1.0 + 0.18 * ease_in_out(clamp(t / max(0.1, give_at)))
    finish_cam(cv, z, 600, 900)
    bars(cv)


# ---------------------------------------------------------------- S8 the reveal (Tokushima)
@scene("sd_reveal")
def sd_reveal(cv: Canvas, t, dur, P, ctx: SceneCtx):
    if clip_bg(cv, P, t):
        _reveal_text(cv, t, P)
        return
    cv.img.paste(gradient(cv.ss, (232, 246, 220), (176, 222, 160)), (0, 0))
    bokeh(cv, t)
    z = 1.0 + 0.12 * ease_in_out(clamp(t / dur))
    r = 330
    cv.glow(lambda d, k: d.ellipse([(540 - 360) * k, (1000 - 300) * k, (540 + 360) * k, (1000 + 320) * k], fill=(255, 255, 255, 255)),
            radius=80, strength=0.5)
    ell(cv, 540, 1000 + r * 0.95, r * 0.9, 40, (40, 80, 30), 70)
    sudachi(cv, 540, 1000, r, t)
    for i in range(6):   # fresh sparkle
        ph = (t * 0.7 + i / 6) % 1
        x, y = 540 + math.cos(i * 2.1) * r * 0.75, 1000 + math.sin(i * 1.7) * r * 0.7
        s = 22 * math.sin(ph * math.pi)
        cv.polygon([(x, y - s), (x + s * 0.25, y), (x, y + s), (x - s * 0.25, y)], fill=(255, 255, 255, 230))
        cv.polygon([(x - s, y), (x, y + s * 0.25), (x + s, y), (x, y - s * 0.25)], fill=(255, 255, 255, 230))
    finish_cam(cv, z, 540, 1000)
    _reveal_text(cv, t, P)


def _reveal_text(cv: Canvas, t, P):
    for i, (txt, at, size, y) in enumerate(P.get("telops", [])):
        p = seg(t, at, 0.4)
        if p <= 0:
            continue
        nxt = P["telops"][i + 1][1] if i + 1 < len(P["telops"]) else None
        if nxt is not None and t > nxt and i < len(P["telops"]) - 1 and not P.get("stack", True):
            continue
        cv.rich_line(504, y, split_emphasis(txt, P.get("emphasis", []), C["ink"], C["accent"]), size,
                     scale=0.75 + 0.25 * ease_out_back(p), alpha=clamp(p * 2), stroke=10)
    if P.get("footnote"):
        cv.text(504, P.get("footnote_y", 650), P["footnote"], 30, C["muted"], family="sans", weight=700, alpha=seg(t, P.get("footnote_at", 2.0), 0.4),
                stroke=4)
