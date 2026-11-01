"""Scenes for 「焼き芋を100万個焼いたら、空はどうなる？」: one sweet potato at home -> counting up ->
a steaming factory town -> 1,000,000 -> the potatoes merge into a giant Naruto-kintoki that flies to the
Naruto strait -> it is sucked into a whirlpool -> water-column explosion -> the whirlpool keeps turning.

Scene colours (sky, sea, potato) are natural; UI elements use brand roles.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from .engine import C, H, W, Canvas, clamp, ease_in_out, ease_out, ease_out_back, lerp, mix, seg, shake, split_emphasis
from .scenes import SceneCtx, counter_text, draw_japan, headline, proj, scene
from .scenes_tokyo import gradient, sky, stamp

SKIN = (150, 50, 82)          # なると金時: red-purple skin
SKIN_DARK = (96, 30, 54)
CHAR = (58, 30, 30)           # 焼き目
FLESH = (244, 186, 62)        # golden flesh
FLESH_HI = (255, 222, 120)
GOLD = (255, 200, 90)
SEA_DEEP = (18, 78, 92)
SEA = (34, 118, 126)
FOAM = (236, 246, 242)
SKY_BLUE = ((96, 150, 196), (214, 232, 240))
SKY_HIGH = ((40, 84, 150), (150, 196, 232))


# ---------------------------------------------------------------- the sweet potato
@lru_cache(maxsize=64)
def _imo_shape(seed: int):
    rnd = random.Random(seed)
    spots = [(rnd.uniform(-0.8, 0.8), rnd.uniform(-0.8, 0.8), rnd.uniform(0.03, 0.08)) for _ in range(9)]
    return rnd.uniform(0.9, 1.1), rnd.uniform(-0.06, 0.06), spots


def draw_imo(cv: Canvas, x, y, L, angle=0.0, seed=1, split=True, glow=0.0, alpha=255):
    """Baked sweet potato centred at (x, y), length L px. Spindle body, charred spots, a split showing
    golden flesh. angle in radians."""
    if L < 3:
        return
    thick, bend, spots = _imo_shape(seed % 64)
    ca, sa = math.cos(angle), math.sin(angle)

    def T(u, v):   # u along the potato (-1..1), v across (in units of L)
        px, py = u * L * 0.5, v * L
        return x + px * ca - py * sa, y + px * sa + py * ca

    def half(u):
        return 0.23 * thick * (1 - u * u) ** 0.42 * (1 + 0.12 * u)

    def mid(u):
        return bend * (1 - u * u)
    if glow > 0:
        cv.glow(lambda d, k: d.polygon([(px * k, py * k) for px, py in
                                        [T(u, mid(u) - half(u) * 1.15) for u in _U] +
                                        [T(u, mid(u) + half(u) * 1.15) for u in reversed(_U)]], fill=GOLD + (255,)),
                radius=max(6, L * 0.08), strength=glow)
    outline = [T(u, mid(u) - half(u)) for u in _U] + [T(u, mid(u) + half(u)) for u in reversed(_U)]
    cv.polygon(outline, fill=SKIN + (alpha,))
    if L < 14:
        return
    shade = [T(u, mid(u) + half(u) * 0.35) for u in _U] + [T(u, mid(u) + half(u)) for u in reversed(_U)]
    cv.polygon(shade, fill=SKIN_DARK + (int(alpha * 0.8),))
    for su, sv, sr in spots:
        if L < 40:
            break
        u = su * 0.85
        px, py = T(u, mid(u) + sv * half(u))
        cv.circle(px, py, sr * L * 0.5, fill=CHAR + (int(alpha * 0.75),))
    cv.line([T(u, mid(u) - half(u) * 0.55) for u in _U[3:-3]], fill=(206, 120, 140, int(alpha * 0.6)),
            width=max(1, L * 0.015))
    for tip in (-1, 1):   # little root tails
        a, b = T(tip * 1.0, mid(tip)), T(tip * 1.12, mid(tip) + 0.01)
        cv.line([a, b], fill=SKIN_DARK + (alpha,), width=max(1, L * 0.012))
    if split and L >= 24:   # the split: golden flesh
        top = [T(u, mid(u) - half(u) * 0.3 - 0.03 * (1 - (u / 0.45) ** 2)) for u in _US]
        bot = [T(u, mid(u) - half(u) * 0.3 + 0.035 * (1 - (u / 0.45) ** 2)) for u in reversed(_US)]
        cv.polygon(top + bot, fill=FLESH + (alpha,))
        cv.line([T(u, mid(u) - half(u) * 0.2) for u in _US[2:-2]], fill=FLESH_HI + (alpha,), width=max(1, L * 0.015))


_U = [i / 20 * 2 - 1 for i in range(21)]
_US = [i / 12 * 0.9 - 0.45 for i in range(13)]


def steam(cv: Canvas, sources, t, rate=1.0, height=260, size=40, strength=0.8, seed=3):
    """Soft rising steam puffs from each (x, y, scale) source."""
    rnd = random.Random(seed)
    puffs = []
    for sx, sy, sc in sources:
        for i in range(int(6 * rate)):
            ph = (t * 0.45 + i / (6 * rate) + rnd.random() * 0.2) % 1
            wob = math.sin(t * 1.7 + i * 1.3 + sx * 0.01) * 22 * sc * ph
            puffs.append((sx + wob, sy - ph * height * sc, size * sc * (0.4 + ph), 1 - ph))
    if not puffs:
        return
    cv.glow(lambda d, k: [d.ellipse([(x - r) * k, (y - r) * k, (x + r) * k, (y + r) * k],
                                    fill=(255, 255, 255, int(255 * a))) for x, y, r, a in puffs],
            radius=size * 0.6, strength=strength)


def cloud(cv: Canvas, x, y, w, alpha=1.0, seed=0):
    rnd = random.Random(seed)
    blobs = [(x + rnd.uniform(-0.5, 0.5) * w, y + rnd.uniform(-0.12, 0.12) * w, rnd.uniform(0.14, 0.3) * w)
             for _ in range(9)]
    cv.glow(lambda d, k: [d.ellipse([(bx - r) * k, (by - r * 0.7) * k, (bx + r) * k, (by + r * 0.7) * k],
                                    fill=(255, 255, 255, 255)) for bx, by, r in blobs],
            radius=w * 0.05, strength=alpha)


# ---------------------------------------------------------------- s1: one potato at home
@scene("imo_home")
def imo_home(cv: Canvas, t, dur, P, ctx: SceneCtx):
    cv.rect(110, 980, 970, 1010, fill=(196, 160, 110, 255), radius=8)          # table
    cv.rect(170, 1010, 200, 1180, fill=(170, 134, 90, 255))
    cv.rect(880, 1010, 910, 1180, fill=(170, 134, 90, 255))
    cv.polygon([(260, 980), (820, 980), (760, 930), (320, 930)], fill=(236, 226, 200, 255))   # paper
    bob = math.sin(t * 2) * 4
    draw_imo(cv, 540, 860 + bob, P.get("size", 420), -0.12, seed=7, glow=0.35)
    steam(cv, [(470, 820, 1.0), (560, 800, 1.1), (640, 815, 0.9)], t, rate=1.2, height=300, size=34)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=300, size=P.get("hsize", 80), stagger=0.1)


# ---------------------------------------------------------------- s2: counting up
STAGES = [(10, 5, 2, 150), (100, 10, 10, 66), (1000, 25, 40, 30), (10000, 40, 60, 18)]


@scene("imo_count")
def imo_count(cv: Canvas, t, dur, P, ctx: SceneCtx):
    s0, s1 = (ctx.lines[0] if ctx.lines else (0.2, dur - 0.5))
    span = max(0.5, s1 - s0)
    k = clamp(int((t - s0) / span * 4), 0, 3) if t >= s0 else 0
    n, cols, rows, L = STAGES[k]
    stage_t = t - (s0 + span * k / 4)
    pop = ease_out_back(clamp(stage_t / 0.35)) if k > 0 or t >= s0 else ease_out_back(clamp(t / 0.35))
    y_top, y_bot = 560, 1170
    cell_w = 840 / cols
    cell_h = (y_bot - y_top) / rows
    cnt = 0
    for r in range(rows):
        for c in range(cols):
            x = 120 + cell_w * (c + 0.5)
            y = y_top + cell_h * (r + 0.5)
            draw_imo(cv, x, y, min(cell_w, cell_h * 2.2) * 0.86 * (0.85 + 0.15 * pop), -0.2 + ((r * 7 + c) % 5) * 0.05,
                     seed=r * 31 + c, split=L > 40)
            cnt += 1
    if k == 0:
        steam(cv, [(120 + cell_w * (c + 0.5), y_top + cell_h * 0.3, 0.5) for c in range(cols)], t, height=200, size=26)
    label = f"{n:,}{P.get('unit', '個')}"
    sc = 0.7 + 0.3 * pop
    cv.text(540, 430, label, 130 * sc, C["accent"], stroke=6)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=290, size=60)


# ---------------------------------------------------------------- s3/s4: factory town in steam
@lru_cache(maxsize=2)
def town(seed=4):
    rnd = random.Random(seed)
    out = []
    x = -40
    while x < W + 40:
        w = rnd.uniform(50, 110)
        out.append((x, w, rnd.uniform(60, 170), rnd.random()))
        x += w + rnd.uniform(4, 16)
    return tuple(out)


def draw_factory_town(cv: Canvas, t, steam_level, cover=0.0, label="焼き芋工場"):
    ground = 1130
    sky(cv, ((178, 204, 214), (240, 232, 214)))
    cv.rect(0, ground, W, H, fill=(150, 140, 120, 255))
    for (x, w, h, tone) in town():
        c = mix((176, 160, 140), (200, 188, 168), tone)
        cv.rect(x, ground - h, x + w, ground, fill=c + (255,))
        cv.polygon([(x - 6, ground - h), (x + w / 2, ground - h - 34), (x + w + 6, ground - h)],
                   fill=mix(c, (120, 70, 60), 0.5) + (255,))
        for j in range(int(h / 40)):
            cv.rect(x + 12, ground - h + 16 + j * 40, x + 26, ground - h + 34 + j * 40, fill=(250, 236, 200, 255))
    fx0, fx1, ftop = 160, 920, 840          # the giant yakiimo factory
    cv.rect(fx0, ftop, fx1, ground, fill=(116, 96, 86, 255))
    cv.polygon([(fx0, ftop)] + [(fx0 + i * (fx1 - fx0) / 6 + d, ftop - (60 if d else 0)) for i in range(6)
                                 for d in (0, (fx1 - fx0) / 12)] + [(fx1, ftop)], fill=(140, 116, 100, 255))
    stacks = []
    for i in range(5):
        sx = fx0 + 70 + i * 150
        cv.rect(sx - 22, ftop - 240, sx + 22, ftop, fill=(150, 70, 60, 255))
        cv.rect(sx - 26, ftop - 250, sx + 26, ftop - 228, fill=(100, 50, 44, 255))
        stacks.append((sx, ftop - 250, 1.0 + steam_level * 1.4))
    cv.rect(fx0 + 40, ftop + 90, fx1 - 40, ftop + 170, fill=(60, 52, 48, 255))      # window with conveyor
    off = (t * 120) % 64
    for i in range(14):
        draw_imo(cv, fx0 + 40 + i * 64 + off - 32, ftop + 130, 54, 0.05, seed=i, split=False)
    cv.text(540, ftop + 250, label, 54, (250, 236, 200), stroke=0)
    steam(cv, stacks, t, rate=1.0 + steam_level * 1.5, height=520, size=60 + 50 * steam_level,
          strength=0.7 + 0.3 * steam_level, seed=9)
    if cover > 0:   # the town disappears into steam
        cv.rect(0, 0, W, H, fill=(255, 255, 255, int(170 * cover)))
        steam(cv, [(x, 1100, 2.4) for x in range(60, W, 160)], t, rate=1.2, height=700, size=120, strength=cover)


@scene("imo_factory")
def imo_factory(cv: Canvas, t, dur, P, ctx: SceneCtx):
    q = ease_in_out(t / max(dur, 0.1))
    draw_factory_town(cv, t, q, cover=0.0, label=P.get("factory_label", "焼き芋工場"))
    cv.rect(140, 380, 940, 520, fill=C["paper"] + (238,), outline=C["sub"] + (255,), width=4, radius=22)
    counter_text(cv, 540, 450, P.get("from", 10000), P.get("to", 500000), ease_in_out(seg(t, 0.2, dur - 0.3)),
                 unit=P.get("unit", "個"), size=100)
    headline(cv, P.get("headline", []), P.get("emphasis", []), t, y0=290, size=60)


@scene("imo_million")
def imo_million(cv: Canvas, t, dur, P, ctx: SceneCtx):
    q = ease_in_out(seg(t, 0, dur * 0.6))
    draw_factory_town(cv, t, 1.0, cover=0.4 + 0.6 * q, label=P.get("factory_label", "焼き芋工場"))
    cp = ease_out(seg(t, 0.0, ctx.line_start(0, 0.3) + 0.9))
    cv.rect(140, 380, 940, 520, fill=C["paper"] + (238,), outline=C["sub"] + (255,), width=4, radius=22)
    counter_text(cv, 540, 450, P.get("from", 500000), P.get("to", 1000000), cp, unit=P.get("unit", "個"), size=100)
    sp = seg(t, ctx.line_start(0, 0.3) + P.get("stamp_delay", 1.0), 0.45)
    stamp(cv, 760, P.get("stamp", ""), P.get("stamp_emphasis", []), sp, size=70)


# ---------------------------------------------------------------- s5: they merge, then fly
@lru_cache(maxsize=1)
def swarm(n=420, seed=5):
    rnd = random.Random(seed)
    return tuple((rnd.uniform(-700, 700), rnd.uniform(-900, 900), rnd.uniform(0, 6.3), rnd.uniform(0.25, 0.75),
                  rnd.randrange(64)) for _ in range(n))


@scene("imo_merge")
def imo_merge(cv: Canvas, t, dur, P, ctx: SceneCtx):
    lift = ctx.line_start(1, dur * 0.55) if len(ctx.lines) > 1 else dur * P.get("lift_at", 0.5)
    fly = clamp((t - lift) / max(0.1, dur - lift))
    # sky darkens to deep blue as we climb
    sky(cv, SKY_BLUE)
    if fly > 0:
        cv.img.alpha_composite(_sky_layer(cv.ss, int(255 * ease_in_out(fly)) // 8 * 8))
    climb = ease_in_out(fly) * 2600
    ground = 1150 + climb
    if ground < H + 400:   # town + mountains for scale
        cv.polygon([(0, ground - 140), (220, ground - 330), (430, ground - 160), (700, ground - 380), (1080, ground - 150),
                    (1080, ground), (0, ground)], fill=(110, 140, 120, 255))
        cv.rect(0, ground, W, ground + 900, fill=(150, 140, 120, 255))
        for (x, w, h, tone) in town(9):
            cv.rect(x, ground - h * 0.35, x + w * 0.6, ground, fill=mix((176, 160, 140), (210, 196, 176), tone) + (255,))
    for i, (cy, w, sd) in enumerate(((ground - 900, 700, 1), (ground - 1500, 900, 2), (ground - 2200, 800, 3),
                                     (ground - 2900, 1000, 4))):
        if -300 < cy < H + 300:
            cloud(cv, 200 + i * 230, cy, w, 0.9, sd)
    m = ease_in_out(seg(t, 0.0, lift - 0.3))          # merging
    big = lerp(120, P.get("size", 760), ease_out(m))
    cx = 540 + math.sin(t * 1.3) * 10 * fly
    cy = lerp(880, 820, m) - math.sin(t * 2.0) * 8
    for (sx, sy, ph, delay, seed) in swarm():
        p = ease_in_out(clamp((m - delay * 0.6) / 0.4))
        if p >= 1:
            continue
        x = lerp(540 + sx, cx, p) + math.sin(ph + t * 3) * 30 * (1 - p)
        y = lerp(880 + sy, cy, p)
        draw_imo(cv, x, y, 70 * (1 - 0.5 * p), ph + t * 2 * (1 - p), seed=seed, split=False)
    draw_imo(cv, cx, cy, big, -0.18 + 0.04 * math.sin(t * 1.5), seed=11, glow=0.25 + 0.5 * m)
    steam(cv, [(cx - big * 0.15, cy - big * 0.12, big / 420), (cx + big * 0.1, cy - big * 0.14, big / 420)], t,
          rate=1.5, height=260, size=40, strength=0.8)
    if P.get("label") and m > 0.95:
        lp = seg(t, lift - 0.4, 0.4)
        cv.text(540, 1180 if fly == 0 else 1180, P["label"], 56, C["accent"], stroke=5, alpha=lp * (1 - fly))


@lru_cache(maxsize=4)
def _sky_layer(ss, a):
    g = gradient(ss, SKY_HIGH[0], SKY_HIGH[1]).copy()
    g.putalpha(a)
    return g


# ---------------------------------------------------------------- Naruto strait (top-down)
STRAIT_W = 520


def strait_land(cv: Canvas, xf):
    """Stylised top view: Shikoku (bottom-left) and Awaji (top-right) with the strait between, plus the bridge."""
    sea_top, sea_bot = SEA, SEA_DEEP
    cv.img.paste(gradient(cv.ss, sea_top, sea_bot), (0, 0))
    shik = [(-2000, 2000), (-2000, -300), (-700, -220), (-420, -60), (-300, 40), (-250, 200), (-280, 420),
            (-180, 700), (-120, 2000)]
    awaj = [(2000, -2000), (120, -2000), (180, -700), (260, -420), (300, -200), (360, -40), (600, 120), (2000, 260)]
    for poly, col in ((shik, (118, 150, 104)), (awaj, (112, 146, 100))):
        pts = [xf(x, y) for x, y in poly]
        cv.polygon(pts, fill=col + (255,))
        cv.line(pts[1:-1], fill=(222, 214, 186, 255), width=10)
    b0, b1 = xf(-290, -60), xf(330, -260)      # 大鳴門橋 (simplified)
    cv.line([b0, b1], fill=(236, 236, 228, 255), width=12)
    for f in (0.3, 0.7):
        px, py = lerp(b0[0], b1[0], f), lerp(b0[1], b1[1], f)
        cv.rect(px - 10, py - 10, px + 10, py + 10, fill=(200, 200, 192, 255))


def sea_whirl(cv: Canvas, cx, cy, R, t, spin=1.0, alpha=1.0, depth=1.0):
    """Natural-looking whirlpool seen from above: darker funnel, white foam spiral arms."""
    if R < 4:
        return
    k = cv.ss
    layer, d = cv.overlay()
    for i in range(10, 0, -1):
        rr = R * i / 10
        col = mix((10, 52, 62), SEA, (i / 10) ** 0.7)
        d.ellipse([(cx - rr) * k, (cy - rr) * k, (cx + rr) * k, (cy + rr) * k], fill=col + (int(200 * alpha * depth),))
    rot = t * spin
    for a_i in range(9):
        base = a_i / 9 * math.tau + rot
        prev = None
        for s in range(70):
            f = s / 69
            rr = R * (0.05 + 0.95 * f)
            a = base + f * 5.0
            p = ((cx + math.cos(a) * rr) * k, (cy + math.sin(a) * rr) * k)
            if prev:
                d.line([prev, p], fill=FOAM + (int(230 * alpha * (0.25 + 0.75 * f) * (1 - 0.6 * f ** 3)),),
                       width=max(1, int((1.5 + 9 * f) * k * R / 300)))
            prev = p
    cv.img.alpha_composite(layer)


def sea_texture(cv: Canvas, xf, t, scale):
    rnd = random.Random(12)
    for _ in range(80):
        x, y = rnd.uniform(-1200, 1200), rnd.uniform(-1600, 1600)
        px, py = xf(x + math.sin(t + x) * 6, y)
        L = 30 * scale
        cv.line([(px - L, py), (px + L, py + 4 * scale)], fill=FOAM + (60,), width=max(1, 2 * scale))


def strait_view(cv: Canvas, t, scale, cx=0.0, cy=0.0, whirl_R=300, whirl_alpha=1.0, spin=1.6):
    def xf(x, y):
        return 540 + (x - cx) * scale, 780 + (y - cy) * scale
    strait_land(cv, xf)
    sea_texture(cv, xf, t, scale)
    for (wx, wy, r, sp) in ((-30, 380, 0.35, 1.3), (160, -520, 0.28, -1.1), (-200, 620, 0.22, 1.5)):
        x, y = xf(wx, wy)
        sea_whirl(cv, x, y, r * whirl_R * scale, t, sp, 0.7)
    x, y = xf(0, 0)
    sea_whirl(cv, x, y, whirl_R * scale, t, spin, whirl_alpha)
    return xf


# ---------------------------------------------------------------- s6: flight to Naruto, stop
@scene("imo_to_naruto")
def imo_to_naruto(cv: Canvas, t, dur, P, ctx: SceneCtx):
    arrive = P.get("arrive_at", 2.4)
    if t < arrive:   # over the clouds, Japan's coast below
        q = ease_in_out(t / max(arrive, 0.1))
        cam = (lerp(136.6, 134.66, q), lerp(35.3, 34.24, q), math.exp(lerp(math.log(260), math.log(1400), q)))
        cv.img.paste(gradient(cv.ss, SEA, SEA_DEEP), (0, 0))
        draw_japan(cv, cam, highlight="JP-36", hl_color=(126, 160, 108), hl_alpha=1.0)
        for i in range(6):
            yy = ((i * 380 + t * 520) % 2400) - 300
            cloud(cv, 120 + (i * 290) % 900, yy, 520, 0.75, i)
        cv.circle(540 + 60, 820 + 70, 70, fill=(0, 0, 0, 50))      # shadow on the clouds
        draw_imo(cv, 540, 820, 300, -1.2, seed=11, glow=0.5)
        steam(cv, [(540, 900, 0.8)], t, rate=1.0, height=-220, size=30, strength=0.6)
        if P.get("chip"):
            from .scenes_tokyo import chip
            chip(cv, 96, 410, P["chip"], t, P.get("live", ""))
    else:            # above the strait; it stops and hangs there (silence)
        tb = t - arrive
        q = ease_out(clamp(tb / 1.4))
        xf = strait_view(cv, t, lerp(1.7, 1.15, q))
        hover = math.sin(t * 1.6) * 6
        x, y = xf(0, 0)
        cv.circle(x + 40, y + 50, 120, fill=(0, 0, 0, 40))
        draw_imo(cv, x, y - 40 + hover, lerp(520, 360, q), -0.5, seed=11, glow=0.45)
        if tb < 0.3:
            cv.rect(0, 0, W, H, fill=(255, 255, 255, int(255 * (1 - tb / 0.3))))
        if P.get("place"):
            pp = seg(t, ctx.line_start(0, 0) + 1.4, 0.4)
            cv.text(540, 330, P["place"], 96 * (0.7 + 0.3 * ease_out_back(pp)), C["ink"], stroke=8, alpha=pp)


# ---------------------------------------------------------------- s7: imo vs whirlpool (no narration)
@lru_cache(maxsize=1)
def droplets(n=260, seed=8):
    rnd = random.Random(seed)
    return tuple((rnd.uniform(-1, 1), rnd.uniform(0.3, 1.0), rnd.uniform(0.6, 1.4), rnd.uniform(4, 12)) for _ in range(n))


@scene("imo_vs_uzu")
def imo_vs_uzu(cv: Canvas, t, dur, P, ctx: SceneCtx):
    T_pull, T_gone, T_calm, T_boom = P.get("pull_at", 1.4), P.get("gone_at", 5.2), P.get("gone_at", 5.2) + 0.4, \
        P.get("boom_at", 6.6)
    if t < T_boom:
        spin = 1.6 + 1.2 * ease_in_out(seg(t, T_pull, T_gone - T_pull))
        zoom = lerp(1.15, 0.85, ease_in_out(seg(t, 0, T_gone)))      # pull back: scale comparison
        xf = strait_view(cv, t, zoom, spin=spin)
        cx, cy = xf(0, 0)
        p = ease_in_out(seg(t, T_pull, T_gone - T_pull))             # pulled in
        if t < T_gone:
            orbit = lerp(220, 0, p ** 1.3) * zoom
            ang = t * (0.8 + 3.5 * p ** 2) + 0.6
            x, y = cx + math.cos(ang) * orbit, cy + math.sin(ang) * orbit - 40 * (1 - p)
            fight = math.sin(t * 9) * 0.25 * (1 - p) * clamp((t - T_pull) * 2)
            L = lerp(360, 40, p ** 1.6) * zoom
            cv.circle(x + 30 * (1 - p), y + 40 * (1 - p), L * 0.32, fill=(0, 0, 0, int(50 * (1 - p))))
            draw_imo(cv, x, y, L, ang * (1 + 2 * p) + fight, seed=11, glow=0.4 * (1 - p))
            if p > 0.6:   # spray as it hits the water
                for i, (dx, up, sp, r) in enumerate(droplets()[:80]):
                    ph = ((t * sp * 2) + i * 0.13) % 1
                    cv.circle(x + dx * 80 * ph, y - up * 60 * ph, r * 0.6 * (1 - ph), fill=FOAM + (int(200 * (1 - ph)),))
        else:             # swallowed: splash ring, then an eerie calm
            tg = t - T_gone
            rp = clamp(tg / 0.8)
            if rp < 1:
                cv.circle(cx, cy, 40 + rp * 260 * zoom, outline=FOAM + (int(230 * (1 - rp)),), width=int(18 * (1 - rp) + 2))
                for (dx, up, sp, r) in droplets()[:140]:
                    a = dx * math.pi
                    d = rp * 220 * sp * zoom
                    cv.circle(cx + math.cos(a) * d, cy + math.sin(a) * d - up * 120 * math.sin(rp * math.pi),
                              r * (1 - rp), fill=FOAM + (255,))
            if t > T_calm:
                cv.rect(0, 0, W, H, fill=(10, 30, 36, int(60 * clamp((t - T_calm) / 0.6))))
    else:                 # the explosion: low side view, water column
        tb = t - T_boom
        sx, sy = shake(t, 22 * math.exp(-tb * 2.2))
        horizon = 1000 + sy
        cv.img.paste(gradient(cv.ss, (120, 160, 190), (226, 228, 222)), (0, 0))
        cv.rect(0, horizon, W, H, fill=SEA + (255,))
        for i in range(12):
            yy = horizon + 20 + i * i * 6
            cv.line([(0, yy), (W, yy + 3)], fill=FOAM + (50,), width=2)
        cv.polygon([(-50, horizon), (80, horizon - 90), (260, horizon - 40), (330, horizon)], fill=(92, 120, 92, 255))
        cv.polygon([(760, horizon), (930, horizon - 70), (1130, horizon - 110), (1130, horizon)], fill=(88, 116, 90, 255))
        rise = ease_out(clamp(tb / 0.9))
        fall = clamp((tb - 1.6) / 1.6)
        top = horizon - 760 * rise * (1 - 0.6 * fall)
        wcol = 110 + 120 * rise + 160 * fall
        col_pts = [(540 + sx - wcol * 0.55, horizon)]
        for i in range(13):
            f = i / 12
            yy = lerp(horizon, top, f)
            ww = wcol * (0.55 - 0.25 * f) + math.sin(t * 13 + i * 1.7) * 14
            col_pts.append((540 + sx - ww, yy))
        right = [(540 + sx + (wcol * (0.55 - 0.25 * (i / 12)) + math.sin(t * 11 + i * 2.3) * 14), lerp(horizon, top, i / 12))
                 for i in range(12, -1, -1)]
        cv.glow(lambda d, k: d.polygon([(x * k, y * k) for x, y in col_pts + right], fill=(255, 255, 255, 255)),
                radius=30, strength=0.9)
        cv.polygon(col_pts + right, fill=(242, 248, 246, 235))
        crown = [(540 + sx + math.cos(a) * wcol * 0.9 * (1 + 0.15 * math.sin(a * 5 + t * 6)),
                  top + math.sin(a) * wcol * 0.45) for a in (i / 18 * math.tau for i in range(18))]
        cv.polygon(crown, fill=(250, 252, 250, 240))
        for (dx, up, sp, r) in droplets():
            tt = tb * sp
            vx, vy = dx * 520, -up * 1100
            x = 540 + sx + vx * tt
            y = top + 40 + vy * tt + 0.5 * 1500 * tt * tt
            if y < horizon + 20:
                cv.circle(x, y, r, fill=(246, 250, 250, 230))
        for k_ in range(3):   # shock rings on the water
            rr = (tb * 420 + k_ * 120)
            cv.d.ellipse([(540 + sx - rr) * cv.ss, (horizon - rr * 0.08) * cv.ss, (540 + sx + rr) * cv.ss,
                          (horizon + rr * 0.08) * cv.ss], outline=FOAM + (int(200 * clamp(1 - rr / 900)),),
                         width=int(6 * cv.ss))
        if tb < 0.25:
            cv.rect(0, 0, W, H, fill=(255, 255, 255, int(255 * (1 - tb / 0.25))))


# ---------------------------------------------------------------- s8: the whirlpool keeps turning
@scene("uzu_ochi")
def uzu_ochi(cv: Canvas, t, dur, P, ctx: SceneCtx):
    xf = strait_view(cv, t, lerp(0.95, 1.05, t / max(dur, 0.1)), spin=1.6)
    if t < 0.3:
        cv.rect(0, 0, W, H, fill=(255, 255, 255, int(200 * (1 - t / 0.3))))
    p = seg(t, P.get("text_at", 0.6), 0.5)
    if p > 0:
        sc = 0.7 + 0.3 * ease_out_back(p)
        cv.rect(96, 560, 912, 900, fill=C["paper"] + (int(244 * clamp(p * 2)),), outline=C["sub"] + (255,), width=8,
                radius=28)
        for i, ln in enumerate(P.get("lines", ["やはり、", "最強は渦潮。"])):
            cv.rich_line(504, 660 + i * 130, split_emphasis(ln, P.get("emphasis", []), C["ink"], C["accent"]),
                         P.get("size", 104), scale=sc, alpha=clamp(p * 2))
