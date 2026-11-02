"""「阿波踊り VS 巨大怪獣」: blocky (voxel-style) 3D city, an original kaiju and giant Awa-odori dancers,
shot like a monster movie (low angles, tracking, whip pans, orbit, slow motion, camera shake).

Everything is choreographed in seconds inside each scene and simulated deterministically
(ballistic debris, cars, the kaiju's knock-back), so any frame can be rendered independently.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

import numpy as np

from .engine import C, W, Canvas, clamp, ease_in_out, ease_out, ease_out_back, lerp, mix, seg, split_emphasis
from .scenes import SceneCtx, scene
from .voxel3d import I3, Camera, Scene3D, ballistic, debris_field, rx, ry, rz

# ---------------------------------------------------------------- palette (scene colours)
K_BODY = (104, 74, 146)
K_DARK = (72, 50, 104)
K_BELLY = (200, 176, 214)
K_CRYSTAL = (70, 206, 196)
K_EYE = (255, 168, 40)
K_CLAW = (240, 236, 222)
SKIN = (240, 204, 168)
STRAW = (216, 180, 104)
WHITE = (246, 244, 236)
AI = (40, 64, 122)          # 藍
PINK = (226, 128, 152)
RED = (200, 56, 56)
GREEN = (48, 133, 90)
ROBES = [AI, PINK, GREEN, RED, (36, 92, 140), WHITE]
BUILD = [(206, 200, 188), (176, 188, 200), (214, 202, 172), (166, 176, 164), (222, 214, 204), (190, 170, 160)]
CARS = [(210, 60, 60), (60, 110, 190), (240, 240, 236), (60, 60, 64), (230, 190, 60)]
DUST = (196, 186, 166)
ROAD = (98, 100, 102)
GROUND = (150, 158, 140)


def V(*a):
    return np.array(a, float)


# ---------------------------------------------------------------- city
@lru_cache(maxsize=1)
def city():
    """Avenue along z (road |x|<15), a plaza around the origin, a side street towards -x at z≈0."""
    rnd = random.Random(7)
    blds = []
    for side in (-1, 1):
        z = -420.0
        while z < 520:
            L = rnd.uniform(18, 40)
            if not (-45 < z + L / 2 < 45):                       # keep the plaza open
                x0 = 24 + rnd.uniform(0, 4)
                w = rnd.uniform(16, 34)
                h = rnd.choice([14, 18, 22, 28, 34, 40, 48, 60, 72])
                if side < 0 and -60 < z + L / 2 < 30:            # side street opening on the left
                    z += L + 6
                    continue
                blds.append((side * (x0 + w / 2), h, z + L / 2, w, L, rnd.choice(BUILD)))
                if rnd.random() < 0.45:                          # second row behind
                    w2 = rnd.uniform(16, 30)
                    blds.append((side * (x0 + w + 8 + w2 / 2), h + rnd.choice([-8, 6, 18, 30]), z + L / 2, w2, L * 0.9,
                                 rnd.choice(BUILD)))
            z += L + rnd.uniform(5, 9)
    for x0 in range(-420, -80, 46):                              # side street buildings
        for zs in (-1, 1):
            h = rnd.choice([16, 22, 30, 40, 52])
            blds.append((x0 + 18, max(12, h), zs * (30 + 14), 34, 26, rnd.choice(BUILD)))
    return tuple(blds)


@lru_cache(maxsize=1)
def parked_cars():
    rnd = random.Random(3)
    out = []
    for i in range(46):
        z = rnd.uniform(-380, 460)
        if -50 < z < 50:
            continue
        out.append((rnd.choice((-11, -5, 5, 11)), z, rnd.choice(CARS)))
    return tuple(out)


def add_city(sc: Scene3D, cars_hidden=(), flung=None):
    for (x, h, z, w, L, col) in city():
        sc.box((x, h / 2, z), (w, h, L), col, edge=False, deco="windows")
        if h > 30:
            sc.box((x, h + 1.5, z), (w * 0.4, 3, L * 0.3), mix(col, (90, 90, 90), 0.3), edge=False)
    for i, (x, z, col) in enumerate(parked_cars()):
        if i in cars_hidden:
            continue
        sc.box((x, 0.8, z), (2.0, 1.6, 4.4), col, edge=False)
        sc.box((x, 2.0, z + 0.3), (1.8, 0.9, 2.4), mix(col, (30, 30, 40), 0.5), edge=False)


def add_ground(sc: Scene3D):
    e = sc.cam.eye
    z0, z1 = e[2] - 700, e[2] + 700
    sc.decals.append((np.array([[-15, 0.02, z0], [15, 0.02, z0], [15, 0.02, z1], [-15, 0.02, z1]]), ROAD))
    sc.decals.append((np.array([[-420, 0.02, -15], [-15, 0.02, -15], [-15, 0.02, 15], [-420, 0.02, 15]]), ROAD))
    sc.decals.append((np.array([[-48, 0.03, -42], [48, 0.03, -42], [48, 0.03, 42], [-48, 0.03, 42]]), (176, 168, 150)))
    zz = math.floor(z0 / 14) * 14
    while zz < z1:
        if not (-42 < zz < 42):
            sc.decals.append((np.array([[-0.3, 0.05, zz], [0.3, 0.05, zz], [0.3, 0.05, zz + 6], [-0.3, 0.05, zz + 6]]),
                              (236, 232, 214)))
        zz += 14
    for i in range(12):                                          # crossing stripes at the plaza edges
        x = -13 + i * 2.3
        for zc in (-46, 46):
            sc.decals.append((np.array([[x, 0.05, zc - 3], [x + 1.2, 0.05, zc - 3], [x + 1.2, 0.05, zc + 3],
                                        [x, 0.05, zc + 3]]), (236, 234, 226)))


# ---------------------------------------------------------------- the kaiju (original design)
STAND_H = 28.5


def kaiju(sc: Scene3D, pos, yaw=0.0, pitch=0.0, roll=0.0, walk=0.0, roar=0.0, swipe=0.0, lean=0.0, t=0.0,
          dazed=False, scale=1.0):
    """Purple, single-horned, crystal-backed brute. pos = centre of mass. Faces -z at yaw 0."""
    pos = np.asarray(pos, float)
    R = ry(yaw) @ rx(pitch) @ rz(roll)

    def part(c, size, col, Rl=I3, **kw):
        sc.box(pos + R @ (np.asarray(c, float) * scale), np.asarray(size, float) * scale, col, R @ Rl, **kw)

    for sd in (-1, 1):                                           # legs
        a = math.sin(walk) * 0.45 * sd
        Rl = rx(a)
        hip = V(sd * 7, -10, 0)
        part(hip + Rl @ V(0, -8.5, 0), (8, 17, 9), K_BODY, Rl)
        part(hip + Rl @ V(0, -17, -2), (10, 3, 13), K_DARK, Rl)
        for cx in (-3, 0, 3):
            part(hip + Rl @ V(cx, -17.5, -9), (1.6, 1.6, 2), K_CLAW, Rl)
    Rt = rx(-lean - 0.12)
    waist = V(0, -8, 0)
    part(waist + Rt @ V(0, 11, 0), (22, 22, 16), K_BODY, Rt)
    part(waist + Rt @ V(0, 9, -8.3), (14, 16, 1.2), K_BELLY, Rt)
    for i, (cx, cy, h) in enumerate(((0, 22, 10), (-5, 17, 8), (5, 17, 8), (0, 12, 7), (-4, 7, 6), (4, 7, 6))):
        part(waist + Rt @ V(cx, cy, 8.5), (3.5, h, 3.5), K_CRYSTAL, Rt @ rx(0.45) @ rz(0.25 * (i % 3 - 1)), glow=True)
    hj = waist + Rt @ V(0, 21, -5)
    Rh = Rt @ rx(roar * 0.45)
    part(hj + Rh @ V(0, 4, -6), (14, 9, 14), K_BODY, Rh)
    hinge = hj + Rh @ V(0, -0.5, -1)
    Rj = Rh @ rx(-roar * 0.65)
    part(hinge + Rj @ V(0, -2, -6), (12.5, 3.5, 12), K_DARK, Rj)
    for sd in (-1, 1):
        part(hinge + Rj @ V(sd * 4, 0.4, -11), (1.6, 1.8, 1.6), K_CLAW, Rj)
        part(hj + Rh @ V(sd * 3.6, 2.6, -11), (1.6, 1.6, 1.4), K_CLAW, Rh)
        part(hj + Rh @ V(sd * 4, 6, -13.1), (3.4, 2.2, 0.6), (60, 60, 70) if dazed else K_EYE, Rh, glow=not dazed)
    part(hj + Rh @ V(0, 10.5, -9), (3, 9, 3), K_CRYSTAL, Rh @ rx(-0.55), glow=True)
    for sd in (-1, 1):                                           # arms
        raise_ = (swipe if sd > 0 else 0.0)
        Ra = Rt @ rx(0.25 + math.sin(walk + (0 if sd > 0 else math.pi)) * 0.2 - raise_ * 2.4) @ rz(sd * 0.35)
        sh = waist + Rt @ V(sd * 13, 17, -2)
        part(sh + Ra @ V(0, -6, 0), (7, 12, 7), K_BODY, Ra)
        el = sh + Ra @ V(0, -12, 0)
        Rf = Ra @ rx(-0.7)
        part(el + Rf @ V(0, -5, -1), (6.5, 11, 6.5), K_DARK, Rf)
        for cx in (-2, 0, 2):
            part(el + Rf @ V(cx, -11.5, -2.5), (1.5, 3.4, 1.5), K_CLAW, Rf)
    p = waist + Rt @ V(0, -2, 7)                                 # tail
    for i in range(4):
        sway = math.sin(t * 2.2 - i * 0.7) * 0.25 * (i + 1)
        Ri = Rt @ rx(0.55 + 0.12 * i) @ ry(sway)
        L = 10 - i * 1.5
        part(p + Ri @ V(0, 0, L / 2), (9 - 2 * i, 8 - 1.8 * i, L), K_BODY if i % 2 == 0 else K_DARK, Ri)
        p = p + Ri @ V(0, 0, L)
    if dazed:                                                    # comic stars above the head
        top = hj + Rh @ V(0, 16, -5)
        for i in range(4):
            a = t * 3 + i * math.tau / 4
            sc.box(pos + R @ ((top + V(math.cos(a) * 9, math.sin(t * 5 + i) * 1.2, math.sin(a) * 9)) * scale),
                   (2.2, 2.2, 2.2), (255, 220, 60), ry(t * 4 + i), glow=True)


# ---------------------------------------------------------------- giant Awa-odori dancers
def dancer(sc: Scene3D, pos, yaw=0.0, phase=0.0, kind="otoko", robe=AI, s=1.0, pose=None, spin=0.0):
    """Blocky giant dancer, feet at pos. Same-side hand and foot go forward together (Awa-odori).
    kind: "otoko" (happi, hachimaki, tabi, low wide stance) / "onna" (yukata, folded straw hat, hands high).
    pose="freeze" = both hands straight up (the moment before the finale)."""
    pos = np.asarray(pos, float)
    R = ry(yaw + spin)
    sn = math.sin(phase)
    side = 1 if sn >= 0 else -1
    amt = abs(sn)
    bob = -amt * (1.2 if kind == "otoko" else 0.6)
    otoko = kind == "otoko"

    def part(c, size, col, Rl=I3, **kw):
        sc.box(pos + R @ (np.asarray(c, float) * s) + V(0, bob * s, 0), np.asarray(size, float) * s, col, R @ Rl, **kw)

    if otoko:
        for sd in (-1, 1):
            fwd = sd == side
            Rl = rx(-0.55 * amt if fwd else 0.15 * amt) @ rz(sd * 0.32)
            hj = V(sd * 3.2, 15, 0)
            part(hj + Rl @ V(0, -4, 0), (4.6, 8, 4.6), WHITE, Rl)
            knee = hj + Rl @ V(0, -8, 0)
            Rs = Rl @ rz(-sd * 0.5) @ rx(0.5 * amt if fwd else 0)
            part(knee + Rs @ V(0, -3.6, 0), (4, 7.2, 4), SKIN, Rs)
            part(knee + Rs @ V(0, -7.6, -1.2), (4.2, 1.8, 6.4), WHITE, Rs)
        Rt = rx(-0.2)
        part(V(0, 21.5, 0), (11.5, 13, 6.8), robe, Rt)
        part(V(0, 21.5, -3.5), (2, 13, 0.5), WHITE, Rt)
        part(V(0, 16.5, 0), (11.8, 2.2, 7.1), RED, Rt)
        head_y, hw = 31.5, 7.2
    else:
        for sd in (-1, 1):
            fwd = sd == side
            lift = 1.2 * amt if fwd else 0
            part(V(sd * 1.7, 0.9 + lift, -0.8 * amt if fwd else 0), (2.6, 1.8, 4.2), (60, 40, 30))
            part(V(sd * 1.7, 2.4 + lift, -0.4 if fwd else 0), (2.2, 1.6, 2.6), WHITE)
        part(V(0, 10.5, 0), (8.6, 15, 6.2), robe, rx(-0.04))
        part(V(0, 21.5, 0), (9.2, 9, 5.8), robe)
        part(V(0, 18.6, 0), (9.6, 2.8, 6.2), RED if robe != RED else (240, 200, 80))
        part(V(0, 20, 3.4), (5, 4, 1.6), RED if robe != RED else (240, 200, 80))
        head_y, hw = 30, 6.4
    part(V(0, head_y, 0), (hw, hw, hw), SKIN)
    part(V(0, head_y + hw / 2 + 0.4, 0.3), (hw + 0.2, 1.2, hw + 0.2), (40, 34, 30))
    for sd in (-1, 1):
        part(V(sd * hw * 0.22, head_y + 0.4, -hw / 2 - 0.1), (0.9, 0.9, 0.2), (30, 30, 30))
    part(V(0, head_y - hw * 0.25, -hw / 2 - 0.1), (hw * 0.32, 0.45, 0.2), (150, 50, 50))
    if otoko:
        part(V(0, head_y + 1.6, 0), (hw + 0.4, 1.2, hw + 0.4), WHITE)
    else:
        Rh = rx(-0.25)
        for sd in (-1, 1):
            part(V(sd * 2.6, head_y + 4.6, -0.6), (6.4, 1.2, 9.5), STRAW, Rh @ rz(-sd * 0.55))
    sh_y = head_y - hw / 2 - 1.6
    for sd in (-1, 1):
        fwd = sd == side
        if pose == "freeze":
            r, bend, f = 3.0, 0.1, 0.0
        elif otoko:
            r, bend, f = 2.1 + 0.25 * amt * fwd, 0.9, (-0.6 * amt if fwd else 0.2)
        else:
            r, bend, f = 2.55 + 0.15 * amt * fwd, 0.55, (-0.5 * amt if fwd else 0.1)
        Ra = rx(f) @ rz(sd * r)
        shp = V(sd * (5.9 if otoko else 4.9), sh_y, 0)
        part(shp + Ra @ V(0, -3.5, 0), (3.2, 7, 3.2), robe, Ra)
        el = shp + Ra @ V(0, -7, 0)
        Rf = Ra @ rz(sd * bend)
        part(el + Rf @ V(0, -3, 0), (2.5, 6, 2.5), SKIN, Rf)
        part(el + Rf @ V(0, -6.3, 0), (2.6, 1.6, 2.6), SKIN, Rf)


# ---------------------------------------------------------------- crowds and effects
@lru_cache(maxsize=4)
def crowd_points(kind: str, n: int, seed=5):
    rnd = np.random.default_rng(seed)
    if kind == "avenue":     # dancers filling the avenue behind the giant
        P = np.stack([rnd.uniform(-14, 14, n), np.zeros(n), rnd.uniform(-420, -48, n)], 1)
    elif kind == "plaza":    # ring around the plaza
        a = rnd.uniform(0, math.tau, n)
        r = rnd.uniform(22, 44, n)
        P = np.stack([np.clip(np.cos(a) * r, -44, 44), np.zeros(n), 12 + np.sin(a) * r], 1)
    elif kind == "city":     # everywhere on the roads
        a = rnd.random(n) < 0.6
        P = np.stack([np.where(a, rnd.uniform(-14, 14, n), rnd.uniform(-420, -16, n)), np.zeros(n),
                      np.where(a, rnd.uniform(-420, 480, n), rnd.uniform(-14, 14, n))], 1)
    else:                    # fleeing citizens
        P = np.stack([rnd.uniform(-13, 13, n), np.zeros(n), rnd.uniform(-20, 70, n)], 1)
    cols = rnd.integers(0, len(ROBES), n)
    heads = rnd.random(n) < 0.5
    return P, cols, heads


def add_crowd(sc: Scene3D, kind, n, t, dance=True, move=None):
    P, cols, heads = crowd_points(kind, n)
    P = P.copy()
    if move is not None:
        P = P + move
    if dance:
        P[:, 1] = np.abs(np.sin(t * 6.7 + np.arange(n) * 0.37)) * 0.35
    for i in range(n):
        body = ROBES[cols[i]] if kind != "flee" else BUILD[cols[i] % len(BUILD)]
        head = STRAW if (heads[i] and kind != "flee") else SKIN
        sc.sprites.append((P[i], 1.7, body, head))


def dust_cloud(sc: Scene3D, origin, t, n=26, seed=1, spread=30.0, rise=10.0, life=3.0, size=7.0):
    if t < 0 or t > life:
        return
    rnd = random.Random(seed)
    q = t / life
    for i in range(n):
        a = rnd.uniform(0, math.tau)
        d = spread * ease_out(min(1, t / (life * 0.6))) * rnd.uniform(0.3, 1.0)
        p = np.asarray(origin, float) + V(math.cos(a) * d, rnd.uniform(1, rise) * ease_out(q) + 2, math.sin(a) * d)
        sc.bills.append((p, size * (0.6 + 1.2 * q) * rnd.uniform(0.7, 1.3), DUST + (int(170 * (1 - q) ** 1.5),)))


def ring(sc: Scene3D, centre, r, width, rgba, segs=48, y=0.08):
    c = np.asarray(centre, float)
    for i in range(segs):
        a0, a1 = i / segs * math.tau, (i + 1) / segs * math.tau
        pts = np.array([[c[0] + math.cos(a0) * r, y, c[2] + math.sin(a0) * r],
                        [c[0] + math.cos(a1) * r, y, c[2] + math.sin(a1) * r],
                        [c[0] + math.cos(a1) * (r + width), y, c[2] + math.sin(a1) * (r + width)],
                        [c[0] + math.cos(a0) * (r + width), y, c[2] + math.sin(a0) * (r + width)]])
        sc.decals.append((pts, rgba))


def shadow(sc: Scene3D, centre, r, alpha=70):
    c = np.asarray(centre, float)
    pts = np.array([[c[0] + math.cos(a) * r, 0.06, c[2] + math.sin(a) * r * 0.8] for a in np.linspace(0, math.tau, 20)])
    sc.decals.append((pts, (40, 40, 40, alpha)))


def debris(sc: Scene3D, field, t, colors=((180, 172, 160), (140, 136, 130), (206, 196, 180), (110, 110, 112))):
    if t < 0:
        return
    for (p0, v0, s, spin, ci) in field:
        p, _ = ballistic(t, p0, v0, rest=s / 2)
        Rb = rx(spin[0] * min(t, 1.5)) @ ry(spin[1] * min(t, 1.5)) @ rz(spin[2] * min(t, 1.5))
        sc.box(p, (s, s, s), colors[ci % len(colors)], Rb, edge=True)


@lru_cache(maxsize=1)
def _bld_boxes():
    b = np.array([(x - w / 2, x + w / 2, z - L / 2, z + L / 2, h) for (x, h, z, w, L, _) in city()])
    return b


def safe_eye(eye):
    """If a shot would put the camera inside a building, lift it above the roof."""
    b = _bld_boxes()
    m = 2.0
    inside = (b[:, 0] - m < eye[0]) & (eye[0] < b[:, 1] + m) & (b[:, 2] - m < eye[2]) & (eye[2] < b[:, 3] + m) & \
             (eye[1] < b[:, 4] + 3)
    if inside.any():
        eye = eye.copy()
        eye[1] = b[inside, 4].max() + 4
    return eye


def shake_cam(eye, target, t, impacts, base=0.0):
    """Hand-held wobble + decaying shakes after each (time, strength) impact."""
    amp = base + sum(s * math.exp(-(t - ti) * 5.5) for ti, s in impacts if t >= ti)
    off = V(math.sin(t * 37.1) + 0.5 * math.sin(t * 91.7), math.sin(t * 43.3 + 1), math.sin(t * 29.9 + 2)) * amp
    roll = math.sin(t * 31.7) * amp * 0.012
    return safe_eye(np.asarray(eye, float) + off), np.asarray(target, float) + off * 0.5, roll


def warp(t, slows):
    """Scene time -> simulation time with slow-motion windows [(start, end, rate)]."""
    out, last = 0.0, 0.0
    for a, b, r in slows:
        if t <= a:
            break
        out += a - last
        out += (min(t, b) - a) * r
        last = min(t, b)
        if t <= b:
            return out
    return out + (t - last)


def streaks(cv: Canvas, amount, horizontal=True):
    if amount <= 0:
        return
    rnd = random.Random(int(amount * 100))
    for _ in range(int(40 * amount)):
        y = rnd.uniform(0, 1920)
        x = rnd.uniform(-200, 1080)
        L = rnd.uniform(200, 700) * amount
        if horizontal:
            cv.line([(x, y), (x + L, y)], fill=(255, 255, 255, int(120 * amount)), width=rnd.uniform(2, 6))
        else:
            cv.line([(y * 0.56, x * 1.7), (y * 0.56, x * 1.7 + L)], fill=(255, 255, 255, int(120 * amount)), width=3)


def flash(cv: Canvas, a, col=(255, 255, 255)):
    if a > 0:
        cv.rect(0, 0, W, 1920, fill=col + (int(255 * clamp(a)),))


def letterbox(cv: Canvas, a=1.0):
    """Thin cinematic bars (inside the Reels UI margins)."""
    cv.rect(0, 0, W, 150, fill=(10, 10, 12, int(230 * a)))
    cv.rect(0, 1920 - 170, W, 1920, fill=(10, 10, 12, int(230 * a)))


def telop(cv: Canvas, lines, emphasis, p, y=330, size=82, panel=True):
    if p <= 0:
        return
    sc = 0.7 + 0.3 * ease_out_back(p)
    hgt = len(lines) * size * 1.3
    if panel:
        cv.rect(96, y - size * 0.8, 912, y - size * 0.8 + hgt + size * 0.3, fill=C["paper"] + (int(236 * clamp(p * 2)),),
                outline=C["accent"] + (255,), width=6, radius=22)
    for i, ln in enumerate(lines):
        cv.rich_line(504, y + i * size * 1.3, split_emphasis(ln, emphasis, C["ink"], C["accent"]), size, scale=sc,
                     alpha=clamp(p * 2), stroke=0 if panel else 8)


# ---------------------------------------------------------------- S1: kaiju arrives
STEP = 1.15


def kaiju_walk(t, z0, speed):
    """Heavy walk: position along -z, leg phase, foot-fall times."""
    z = z0 - speed * t
    phase = t / STEP * math.pi
    bob = -abs(math.sin(phase)) * 1.4
    return z, phase, bob


@scene("kaiju_arrival")
def kaiju_arrival(cv: Canvas, t, dur, P, ctx: SceneCtx):
    falls = [STEP * (i + 0.5) for i in range(6)]
    impacts = [(f, 2.2) for f in falls]
    kz, ph, bob = kaiju_walk(t, 132, 4.0)
    if t < 1.9:                                   # A: ground-level, the foot slams down
        eye, tgt = V(9, 0.8, kz - 44), V(-3, 9 + t * 3, kz - 4)
        fov = 72
    elif t < 3.6:                                 # B: weave between buildings, full body
        q = ease_in_out((t - 1.9) / 1.7)
        eye, tgt = V(lerp(13, -12, q), 5 + 9 * q, kz - 100 + 18 * q), V(0, 30, kz)
        fov = 58
    else:                                         # C: look up at the face, rush in
        q = ease_in_out((t - 3.6) / max(0.1, dur - 3.6))
        eye, tgt = V(lerp(12, 5, q), lerp(3, 9, q), kz - lerp(34, 22, q)), V(0, 48, kz - 8)
        fov = lerp(64, 52, q)
        impacts = impacts + [(4.15, 3.5)]
    eye, tgt, roll = shake_cam(eye, tgt, t, impacts)
    sc = Scene3D(Camera(eye, tgt, fov, roll), sky=((124, 150, 170), (226, 214, 196)), fog=(214, 206, 192))
    add_ground(sc)
    add_city(sc)
    shadow(sc, (0, 0, kz), 22)
    roar = ease_out(seg(t, 4.1, 0.35)) * (1 - seg(t, dur - 0.3, 0.3))
    kaiju(sc, (0, STAND_H + bob, kz), walk=ph, roar=roar, lean=0.1, t=t)
    for i, f in enumerate(falls):
        dust_cloud(sc, (7 if i % 2 else -7, 0, kz + 6), t - f, n=14, seed=i, spread=14, rise=4, life=1.6, size=4)
    sc.render(cv, GROUND)
    letterbox(cv)
    telop(cv, P.get("telop", ["緊急事態。", "巨大怪獣が出現。"]), P.get("emphasis", ["巨大怪獣"]),
          seg(t, P.get("telop_at", 0.3), 0.35), y=330, size=80)


# ---------------------------------------------------------------- S2: rampage
@lru_cache(maxsize=2)
def swipe_debris():
    return debris_field(11, 46, (-9, 0, 82), power=28, up=1.0, size=(1.2, 4.0))


@lru_cache(maxsize=2)
def swipe_cars():
    rnd = np.random.default_rng(4)
    return [(V(x, 0.8, z), V(rnd.uniform(-14, 14), rnd.uniform(18, 30), rnd.uniform(-30, -10)), c)
            for x, z, c in [(-11, 74, CARS[0]), (-5, 80, CARS[1]), (5, 70, CARS[2]), (11, 86, CARS[4]), (-11, 90, CARS[3])]]


@scene("kaiju_rampage")
def kaiju_rampage(cv: Canvas, t, dur, P, ctx: SceneCtx):
    hit = 2.45
    slows = [(2.35, 3.25, 0.32)]
    st = warp(t, slows)
    kz = 104 - 3.2 * min(st, 2.3)
    swipe = clamp(1 - abs(st - 2.0) / 0.9) if st < 2.9 else 0.0
    roar = ease_out(seg(st, 4.6, 0.3))
    impacts = [(hit, 4.0)]
    if t < 2.2:                                    # A: hand-held, fleeing with the people
        q = t / 2.2
        eye, tgt = V(4 + math.sin(t * 3) * 0.6, 2.2, 36 - 8 * q), V(-2, 26, kz)
        fov, base = 66, 0.25
    elif t < 4.0:                                  # B: side view of the swipe impact (slow motion)
        q = (t - 2.2) / 1.8
        eye, tgt = V(-13, 5 + 2 * q, 30 + 4 * q), V(-4, 14, 84)
        fov, base = 60, 0.0
    else:                                          # C: orbit while it roars
        q = ease_in_out((t - 4.0) / max(0.1, dur - 4.0))
        eye, tgt = V(lerp(13, -11, q), 8 + 16 * q, kz - 95 + 10 * q), V(0, 32, kz)
        fov, base = 56, 0.0
        impacts = impacts + [(4.6, 2.6)]
    eye, tgt, roll = shake_cam(eye, tgt, st, impacts, base)
    sc = Scene3D(Camera(eye, tgt, fov, roll), sky=((118, 138, 156), (220, 206, 188)), fog=(208, 198, 184))
    add_ground(sc)
    add_city(sc)
    shadow(sc, (0, 0, kz), 22)
    kaiju(sc, (0, STAND_H, kz), walk=st * 2.4, swipe=swipe, roar=roar, lean=0.18, t=st)
    for i, (p0, v0, col) in enumerate(swipe_cars()):
        if st >= hit:
            p, _ = ballistic(st - hit, p0, v0, rest=0.8)
            spin = min(st - hit, 1.2) * (3 + i)
            sc.box(p, (2.0, 1.6, 4.4), col, rx(spin) @ rz(spin * 0.6), edge=False)
        else:
            sc.box(p0, (2.0, 1.6, 4.4), col, edge=False)
    debris(sc, swipe_debris(), st - hit)
    dust_cloud(sc, (-8, 0, 82), st - hit, n=30, seed=4, spread=34, rise=16, life=3.4, size=8)
    if st >= hit:
        for i in range(10):                         # cracks
            a = i / 10 * math.tau
            r = min(1, (st - hit) * 4) * 18
            sc.decals.append((np.array([[-8, 0.07, 82], [-8 + math.cos(a) * r, 0.07, 82 + math.sin(a) * r],
                                        [-8 + math.cos(a + 0.05) * r, 0.07, 82 + math.sin(a + 0.05) * r]]), (50, 50, 50)))
    add_crowd(sc, "flee", 260, t, dance=False, move=V(0, 0, -9 * t))
    sc.render(cv, GROUND)
    letterbox(cv)
    flash(cv, 0.5 * (1 - seg(st, hit, 0.15)) if st >= hit else 0)


# ---------------------------------------------------------------- S3: the dancers arrive
BEAT = 60 / 128


@scene("awa_arrive")
def awa_arrive(cv: Canvas, t, dur, P, ctx: SceneCtx):
    kz = 80
    dx = lerp(-150, -26, ease_out(seg(t, 0.9, 2.2)))           # the giant steps out of the side street
    dyaw = lerp(-math.pi / 2, -math.pi * 0.9, seg(t, 2.6, 0.9))
    ph = t * math.pi / BEAT
    impacts = [(0.95 + i * BEAT * 2, 1.0) for i in range(4)]
    whip = 0.0
    if t < 1.1:                                    # A: looking up at the kaiju ... whip pan 180°
        a = ease_in_out(seg(t, 0.75, 0.35)) * math.pi
        eye = V(4, 3, 30)
        look = V(math.sin(a) * -60, lerp(38, 20, a / math.pi), math.cos(a) * 50)
        tgt = eye + look
        whip = clamp(1 - abs(t - 0.92) / 0.18)
        fov = 64
    elif t < 3.7:                                  # B: crane up the giant, feet -> face
        q = ease_in_out((t - 1.1) / 2.6)
        eye, tgt = V(dx + 26, lerp(1.5, 30, q), -8), V(dx, lerp(2, 32, q), 0)
        fov = 66
    else:                                          # C: dolly forward on the drums -> face-off two-shot
        steps = (t - 3.7) / (BEAT * 2)
        q = (math.floor(steps) + ease_out(steps % 1)) / max(1, (dur - 3.7) / (BEAT * 2))
        eye, tgt = V(-40, 9, lerp(-100, -66, clamp(q))), V(-8, 24, 30)
        fov = 54
    eye, tgt, roll = shake_cam(eye, tgt, t, impacts)
    sc = Scene3D(Camera(eye, tgt, fov, roll), sky=((132, 160, 186), (236, 220, 196)), fog=(220, 210, 194))
    add_ground(sc)
    add_city(sc)
    shadow(sc, (0, 0, kz), 22)
    kaiju(sc, (0, STAND_H, kz), walk=0.3, roar=0.25 * (1 + math.sin(t * 2)) / 2, lean=0.15, t=t)
    shadow(sc, (dx, 0, 0), 12)
    dancer(sc, (dx, 0, 0), yaw=dyaw, phase=ph, kind="otoko", robe=AI)
    if t > 2.0:
        add_crowd(sc, "avenue", 1400, t)
    sc.render(cv, GROUND)
    letterbox(cv)
    streaks(cv, whip)


# ---------------------------------------------------------------- S4: the fight
CHARGE_END = 2.0
DODGE = (2.0, 2.6)
CRASH = 3.0
SPIN_HIT = 7.6


@lru_cache(maxsize=2)
def crash_debris():
    return debris_field(21, 40, (0, 0, -36), power=22, up=1.1, size=(1.0, 3.6))


def battle_state(st):
    """Kaiju + giant positions for simulation time st."""
    if st < CHARGE_END:                            # charge
        kz = lerp(80, 2, ease_in_out(st / CHARGE_END))
        k = dict(pos=V(0, STAND_H, kz), pitch=0.0, walk=st * 6, lean=0.45, roll=0.0, yaw=0.0)
    elif st < CRASH:                               # stumble past the dodge, fall forward
        q = (st - CHARGE_END) / (CRASH - CHARGE_END)
        kz = lerp(2, -34, ease_out(q))
        pitch = -1.45 * ease_in_out(q)
        k = dict(pos=V(0, lerp(STAND_H, 10, ease_in_out(q)), kz), pitch=pitch, walk=st * 6, lean=0.45, roll=0.0, yaw=0.0)
    elif st < 5.2:                                 # lying, then getting up wobbling
        q = ease_in_out(seg(st, 4.0, 1.2))
        k = dict(pos=V(0, lerp(10, STAND_H, q), -34), pitch=lerp(-1.45, 0, q), walk=0, lean=0.2,
                 roll=math.sin(st * 9) * 0.12 * q, yaw=math.pi)
    elif st < SPIN_HIT:                            # wobbling on the shaking ground
        k = dict(pos=V(0, STAND_H, -34), pitch=math.sin(st * 7) * 0.08, walk=st * 2, lean=0.2,
                 roll=math.sin(st * 6.3) * 0.18, yaw=math.pi + math.sin(st * 3) * 0.2)
    else:                                          # caught in the spin, thrown down the avenue
        ft = st - SPIN_HIT
        p, landed = ballistic(ft, V(0, STAND_H, -34), V(0, 20, 22), g=26, rest=9)
        spin = 7 * min(ft, 2.2) + 1.2 * max(0, min(ft - 2.2, 0.8))
        k = dict(pos=p, pitch=-min(1.45, ft * 1.2), walk=0, lean=0.2, roll=0.0, yaw=math.pi + spin)
    if st < DODGE[0]:
        d = dict(pos=V(0, 0, -22), yaw=math.pi, spin=0.0)
    elif st < DODGE[1]:
        q = ease_out((st - DODGE[0]) / (DODGE[1] - DODGE[0]))
        d = dict(pos=V(lerp(0, -30, q), 4 * math.sin(q * math.pi), -22), yaw=math.pi, spin=q * math.tau)
    elif st < 6.4:
        d = dict(pos=V(-30, 0, -22), yaw=math.pi * 0.75, spin=0.0)
    else:
        q = ease_in_out(seg(st, 6.4, 0.8))
        d = dict(pos=V(lerp(-30, -6, q), 0, lerp(-22, -40, q)), yaw=0.0,
                 spin=max(0, st - 6.9) * 10 * (1 - seg(st, SPIN_HIT + 0.8, 0.6)))
    return k, d


@scene("awa_battle")
def awa_battle(cv: Canvas, t, dur, P, ctx: SceneCtx):
    slows = [(2.9, 3.6, 0.3), (8.0, 8.9, 0.3)]
    st = warp(t, slows)
    k, d = battle_state(st)
    ph = st * math.pi / BEAT
    impacts = [(CRASH, 4.5), (SPIN_HIT, 3.0)] + [(4.3 + i * BEAT, 0.9) for i in range(5)]
    kz = k["pos"][2]
    if t < 1.9:                                    # A: tracking alongside the charge
        eye, tgt = V(13, 8, kz - 62), V(0, 26, kz)
        fov = 66
    elif t < 2.75:                                 # B: whip sideways with the dodge
        q = ease_in_out((t - 1.9) / 0.85)
        eye, tgt = V(lerp(12, -12, q), 9, -70), V(d["pos"][0], 20, -22)
        fov = 62
    elif t < 4.4:                                  # C: low wide on the crash (slow motion)
        eye, tgt = V(36, 3, 4), V(0, 8, -36)
        fov = 64
    elif t < 5.4:                                  # D: ultra-low at the stamping feet
        eye, tgt = V(-12, 0.8, 4), V(-30, 9, -22)
        fov = 74
    elif t < 6.5:                                  # E: top-down on the formation + ground ripples
        q = (t - 5.4) / 1.1
        eye, tgt = V(-12, 170 - 20 * q, -30), V(-12, 0, -31)
        fov = 58
    elif t < 8.6:                                  # F: orbit around both as the spin starts
        q = (t - 6.5) / 2.1
        a = lerp(0.3, 2.1, ease_in_out(q))
        mid = V(-7, 22, -22)
        eye, tgt = mid + V(math.cos(a) * 46, 12, math.sin(a) * 46), mid
        fov = 72
    else:                                          # G: chase the flying kaiju, slam into the street
        eye, tgt = V(12, 24, kz - 72), k["pos"] + V(0, 0, 4)
        fov = 60
    eye, tgt, roll = shake_cam(eye, tgt, st, impacts)
    sc = Scene3D(Camera(eye, tgt, fov, roll), sky=((132, 160, 186), (236, 220, 196)), fog=(220, 210, 194))
    add_ground(sc)
    add_city(sc)
    kp = k["pos"]
    shadow(sc, (kp[0], 0, kp[2]), 22, alpha=int(70 * clamp(1 - (kp[1] - STAND_H) / 40)))
    kaiju(sc, kp, yaw=k["yaw"], pitch=k["pitch"], roll=k["roll"], walk=k["walk"], lean=k["lean"],
          roar=0.3 if 4.8 < st < 6.0 else 0.0, t=st)
    shadow(sc, (d["pos"][0], 0, d["pos"][2]), 12)
    dancer(sc, d["pos"], yaw=d["yaw"], phase=ph, kind="otoko", robe=AI, spin=d["spin"])
    debris(sc, crash_debris(), st - CRASH)
    dust_cloud(sc, (0, 0, -36), st - CRASH, n=34, seed=7, spread=40, rise=18, life=3.5, size=9)
    if 4.2 < st < 7.4:                             # stamping: ripple rings + small bounce of loose debris
        for i in range(5):
            r = ((st - 4.2) / BEAT - i) * 26
            if 0 < r < 120:
                ring(sc, (-30, 0, -22), r, 2.2, (240, 236, 220, int(150 * (1 - r / 120))), segs=36)
    if st > 6.9:                                   # the spinning vortex
        for i in range(3):
            r = 18 + i * 9 + (st * 30 % 9)
            ring(sc, d["pos"], r, 1.6, (255, 255, 255, 110), segs=32, y=0.1)
        dust_cloud(sc, d["pos"], (st - 6.9) % 1.6, n=18, seed=9, spread=26, rise=8, life=1.6, size=6)
    if st > SPIN_HIT + 0.5:
        ft = st - SPIN_HIT
        _, landed = ballistic(ft, V(0, STAND_H, -34), V(0, 20, 22), g=26, rest=9)
        if landed is not None:
            dust_cloud(sc, (kp[0], 0, kp[2]), ft - landed, n=36, seed=12, spread=46, rise=16, life=3, size=10)
    add_crowd(sc, "avenue", 1200, st)
    sc.render(cv, GROUND)
    letterbox(cv)
    flash(cv, 0.6 * (1 - seg(st, CRASH, 0.12)) if st >= CRASH else 0)
    flash(cv, 0.45 * (1 - seg(st, SPIN_HIT, 0.12)) if st >= SPIN_HIT else 0)
    streaks(cv, clamp(1 - abs(t - 2.3) / 0.35) * 0.8)


# ---------------------------------------------------------------- S5: the finale
FIN_K = V(0, STAND_H, 12)
POSE_AT = 5.5
BLAST = 6.9


def finale_kaiju(st):
    if st < 1.6:                                   # getting up from the street
        q = ease_in_out(seg(st, 0.0, 1.6))
        return dict(pos=V(0, lerp(9, STAND_H, q), 12), pitch=lerp(-1.4, 0, q), roar=0.0, dazed=False)
    if st < BLAST:
        return dict(pos=FIN_K, pitch=0.0, roar=ease_out(seg(st, 1.6, 0.4)) * (1 - seg(st, 3.4, 0.5)), dazed=False)
    ft = st - BLAST
    p, landed = ballistic(ft, FIN_K, V(0, 28, 46), g=26, rest=9)
    return dict(pos=p, pitch=-min(1.5, ft * 1.4), roar=0.0, dazed=landed is not None, landed=landed, ft=ft)


GIANTS = [(0.0, "otoko", AI), (math.pi / 2, "onna", PINK), (math.pi, "otoko", RED), (3 * math.pi / 2, "onna", GREEN)]


@scene("awa_finale")
def awa_finale(cv: Canvas, t, dur, P, ctx: SceneCtx):
    slows = [(6.8, 7.9, 0.28)]
    st = warp(t, slows)
    k = finale_kaiju(st)
    impacts = [(1.7, 3.0), (BLAST, 6.0)] + [(2.0 + i * BEAT, 0.6 + 0.15 * i) for i in range(int((POSE_AT - 2) / BEAT))]
    if k.get("landed") is not None:
        impacts.append((BLAST + k["landed"], 5.0))
    if t < 2.0:                                    # A: low angle as it rises and roars
        eye, tgt = V(9, 1.5, -46), V(0, 40, 12)
        fov = 66
    elif t < 4.0:                                  # B: top-down: the giants surround it
        q = (t - 2.0) / 2.0
        a = 0.4 * q
        eye, tgt = V(math.sin(a) * 30, 210 - 30 * q, 12 + math.cos(a) * 30), V(0, 0, 12)
        fov = 60
    elif t < 6.6:                                  # C: step closer on every drum beat
        steps = (t - 4.0) / BEAT
        q = (math.floor(steps) + ease_out(steps % 1)) / ((6.6 - 4.0) / BEAT)
        eye, tgt = V(3, lerp(50, 42, q), lerp(-110, -62, clamp(q))), V(0, 30, 12)
        fov = 58
    elif t < 9.0:                                  # D: pull way back to catch the shock wave (slow motion)
        q = ease_out((t - 6.6) / 2.4)
        eye, tgt = V(lerp(10, 12, q), lerp(30, 190, q), lerp(-80, -230, q)), V(0, 20, 50)
        fov = 60
    else:                                          # E: it crashes down far away, eyes out
        eye, tgt = V(13, 56, k["pos"][2] - 95), k["pos"]
        fov = 56
    eye, tgt, roll = shake_cam(eye, tgt, st, impacts)
    sc = Scene3D(Camera(eye, tgt, fov, roll), sky=((150, 120, 140), (244, 204, 160)), fog=(226, 196, 170))
    add_ground(sc)
    add_city(sc)
    kp = k["pos"]
    shadow(sc, (kp[0], 0, kp[2]), 22)
    kaiju(sc, kp, pitch=k["pitch"], roar=k["roar"], dazed=k["dazed"], lean=0.12, t=st, walk=0.2)
    ph = st * math.pi / BEAT
    enter = ease_out(seg(st, 1.8, 1.8))
    for i, (a, kind, robe) in enumerate(GIANTS):
        r = lerp(120, 40, enter)
        pos = V(math.sin(a) * r, 0, 12 + math.cos(a) * r)
        yaw = math.atan2(-math.sin(a), -math.cos(a)) + math.pi
        pose = "freeze" if POSE_AT <= st < BLAST - 0.15 else None
        shadow(sc, (pos[0], 0, pos[2]), 12)
        dancer(sc, pos, yaw=yaw, phase=ph + i * 0.5, kind=kind, robe=robe, pose=pose)
    add_crowd(sc, "plaza", 900, st)
    if BLAST - 0.6 < st < BLAST:                   # rings converge on the kaiju
        q = (st - (BLAST - 0.6)) / 0.6
        ring(sc, FIN_K, lerp(52, 4, q), 3, (255, 236, 180, 180))
    if st >= BLAST:                                # the shock wave
        ft = st - BLAST
        r = ft * 120
        if r < 600:
            ring(sc, FIN_K, r, 6 + ft * 8, (255, 250, 236, int(200 * clamp(1 - r / 600))), segs=64)
            for j in range(40):
                a = j / 40 * math.tau
                sc.bills.append((V(math.cos(a) * r, 3 + 4 * math.sin(j), 12 + math.sin(a) * r), 9 + ft * 6,
                                 DUST + (int(150 * clamp(1 - r / 600)),)))
    if k.get("landed") is not None:
        dust_cloud(sc, (kp[0], 0, kp[2]), k["ft"] - k["landed"], n=40, seed=31, spread=60, rise=20, life=3.5, size=12)
    sc.render(cv, GROUND)
    letterbox(cv)
    flash(cv, 0.8 * (1 - seg(st, BLAST, 0.2)) if st >= BLAST else 0, (255, 244, 214))


# ---------------------------------------------------------------- S6: victory
@scene("awa_victory")
def awa_victory(cv: Canvas, t, dur, P, ctx: SceneCtx):
    kpos = V(0, 9, 190)
    ph = t * math.pi / BEAT
    if t < 3.4:                                    # A: kaiju down in front, the winner rises in the back
        q = ease_in_out(t / 3.4)
        eye, tgt = V(12, lerp(1.5, 12, q), 272), V(0, lerp(14, 34, q), 140)
        fov = 60
    else:                                          # B: crane up over the whole city
        q = ease_in_out(seg(t, 3.4, dur - 3.4))
        eye, tgt = V(lerp(12, 120, q), lerp(12, 420, q), lerp(272, 340, q)), V(0, 0, lerp(140, 60, q))
        fov = 60
    eye, tgt, roll = shake_cam(eye, tgt, t, [], base=0.0)
    sc = Scene3D(Camera(eye, tgt, fov, roll), sky=((150, 186, 214), (246, 232, 206)), fog=(232, 222, 204),
                 fog_end=1200)
    add_ground(sc)
    add_city(sc)
    kaiju(sc, kpos, pitch=-1.5, dazed=True, t=t)
    for i, (x, z, kind, robe) in enumerate(((0, 150, "otoko", AI), (-10, 124, "onna", PINK),
                                            (10, 120, "otoko", RED), (0, 96, "onna", GREEN))):
        shadow(sc, (x, 0, z), 12)
        dancer(sc, (x, 0, z), yaw=0.0, phase=ph + i * 0.7, kind=kind, robe=robe)
    add_crowd(sc, "city", 2600, t)
    sc.render(cv, GROUND)
    letterbox(cv, 1 - seg(t, 3.4, 1.0))
    p = seg(t, P.get("text_at", 3.8), 0.45)
    if p > 0:
        sc_ = 0.7 + 0.3 * ease_out_back(p)
        cv.rect(96, 600, 912, 940, fill=C["paper"] + (int(240 * clamp(p * 2)),), outline=C["accent"] + (255,),
                width=8, radius=28)
        for i, ln in enumerate(P.get("lines", ["結論。", "阿波踊り、最強。"])):
            cv.rich_line(504, 700 + i * 130, split_emphasis(ln, P.get("emphasis", ["最強"]), C["ink"], C["accent"]),
                         104, scale=sc_, alpha=clamp(p * 2))
        sp = seg(t, P.get("text_at", 3.8) + 0.9, 0.4)
        if P.get("sub"):
            cv.text(504, 1010, P["sub"], 52 * (0.8 + 0.2 * ease_out_back(sp)), C["paper"], alpha=sp, stroke=8,
                    stroke_fill=(30, 30, 34))
