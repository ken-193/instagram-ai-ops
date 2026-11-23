"""Smooth, rounded 3D kit (no blocky / voxel look): soft-toy people, a porcelain maneki-neko and a
Japanese shotengai. Same idea as blocky.py: parts are parented to joint empties, so pose(t) only
rotates joints and every frame is a pure function of t (parallel rendering).
"""
from __future__ import annotations

import math
import random

import bpy

from .core import empty, mat

_M: dict = {}


def lin(rgb):
    return tuple(c ** 2.2 for c in rgb)


def m(rgb, rough=0.55, coat=0.0, metal=0.0, emit=None, sss=0.0, key=None):
    """Cached material from a display-space colour."""
    k = key or (tuple(round(c, 3) for c in rgb), rough, coat, metal, emit, sss)
    if k not in _M:
        e = (lin(emit[0]), emit[1]) if emit else None
        mm = mat("sm%d" % len(_M), lin(rgb), rough, coat=coat, sss=sss, emit=e)
        if metal:
            mm.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = metal
        _M[k] = mm
    return _M[k]


def joint(name, loc, parent=None):
    j = empty(name, loc)
    if parent is not None:
        j.parent = parent
    return j


def ball(loc, scale, material, parent=None, seg=32, name="ball"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(8, seg // 2), location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale if isinstance(scale, tuple) else (scale, scale, scale)
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    if parent is not None:
        o.parent = parent
    return o


def rbox(loc, size, material, parent=None, bevel=0.08, segs=3, name="rbox"):
    """Box with rounded edges (bevel modifier) and smooth shading."""
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL")
        b.width, b.segments, b.limit_method = min(bevel, min(size) * 0.45), segs, "NONE"
        bpy.ops.object.shade_smooth()
        try:
            o.data.shade_smooth()
        except Exception:
            pass
    o.data.materials.append(material)
    if parent is not None:
        o.parent = parent
    return o


def cone(loc, r1, r2, depth, material, parent=None, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    if parent is not None:
        o.parent = parent
    return o


def torus(loc, major, minor, material, parent=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(location=loc, rotation=rot, major_radius=major, minor_radius=minor,
                                     major_segments=48, minor_segments=16)
    o = bpy.context.object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    if parent is not None:
        o.parent = parent
    return o


# ---------------------------------------------------------------- palettes
PORCELAIN = (0.96, 0.95, 0.91)
SKIN = [(0.96, 0.8, 0.66), (0.86, 0.66, 0.5), (0.62, 0.43, 0.3)]
HAIR = [(0.07, 0.06, 0.06), (0.25, 0.16, 0.1), (0.72, 0.72, 0.72)]
CLOTH = [(0.2, 0.45, 0.75), (0.85, 0.35, 0.3), (0.3, 0.6, 0.38), (0.92, 0.76, 0.32), (0.5, 0.4, 0.65),
         (0.96, 0.96, 0.93), (0.18, 0.22, 0.36), (0.9, 0.55, 0.65)]
YUKATA = [(0.95, 0.45, 0.6), (0.3, 0.55, 0.85), (0.98, 0.75, 0.3), (0.55, 0.35, 0.75), (0.95, 0.35, 0.3),
          (0.35, 0.7, 0.6)]


# ---------------------------------------------------------------- the giant maneki-neko
class ManekiNeko:
    """Porcelain beckoning cat, faces -y, base at loc. height ~= 30 * s metres.
    Joints: body (sway), head, paw_r (raised beckoning paw, viewer's left), paw_l (holds the koban), leg_r/leg_l."""

    def __init__(self, loc=(0, 0, 0), s=1.0, name="neko"):
        self.s = s
        W, R, P, G, K = (m(PORCELAIN, 0.18, coat=0.7), m((0.78, 0.06, 0.06), 0.3, coat=0.5),
                         m((0.97, 0.62, 0.66), 0.4, coat=0.3), m((0.98, 0.76, 0.3), 0.25, metal=1.0),
                         m((0.05, 0.04, 0.04), 0.3, coat=0.4))
        self.root = joint(name, loc)
        self.body = joint(name + "_body", (0, 0, 0), self.root)
        ball((0, 0, 10.5 * s), (8.5 * s, 7.5 * s, 10.5 * s), W, self.body, seg=48)              # torso
        self.legs = []
        for sd in (-1, 1):                                                                         # feet / legs
            j = joint(name + "_leg", (sd * 4.2 * s, -3.5 * s, 3.0 * s), self.body)
            ball((0, -1.2 * s, -1.4 * s), (3.0 * s, 3.8 * s, 2.0 * s), W, j)
            self.legs.append(j)
        ball((0, 6.8 * s, 4 * s), (2.0 * s, 3.5 * s, 2.0 * s), W, self.body)                     # tail
        torus((0, 0, 17.6 * s), 6.3 * s, 0.9 * s, R, self.body)                                  # red collar
        ball((0, -6.6 * s, 16.4 * s), 1.6 * s, G, self.body)                                     # bell
        self.head = joint(name + "_head", (0, 0, 18.0 * s), self.body)
        ball((0, 0, 6.0 * s), (8.6 * s, 7.6 * s, 7.0 * s), W, self.head, seg=48)
        for sd in (-1, 1):                                                                         # ears
            ear = cone((sd * 5.0 * s, 0.5 * s, 12.0 * s), 2.8 * s, 0.25 * s, 4.6 * s, W, self.head,
                       rot=(0, sd * -0.35, 0))
            cone((sd * 5.0 * s, -0.4 * s, 11.8 * s), 1.9 * s, 0.15 * s, 3.4 * s, P, self.head, rot=(0, sd * -0.35, 0))
        # face: open eyes (ovals) and happy eyes (^ marks); pose toggles them with scale
        self.eyes_open, self.eyes_happy = [], []
        for sd in (-1, 1):
            ball((sd * 3.1 * s, -6.9 * s, 7.2 * s), (1.15 * s, 0.35 * s, 1.45 * s), m((0.98, 0.85, 0.3), 0.2, coat=0.6), self.head)
            self.eyes_open.append(ball((sd * 3.1 * s, -7.15 * s, 7.2 * s), (0.45 * s, 0.4 * s, 1.15 * s), K, self.head))
            hj = joint(name + "_heye", (sd * 3.1 * s, -7.2 * s, 7.2 * s), self.head)
            for k in (-1, 1):
                b = ball((k * 0.55 * s, 0, 0.1 * s), (0.75 * s, 0.25 * s, 0.22 * s), K, hj)
                b.rotation_euler = (0, k * 0.6, 0)
            hj.scale = (0.001, 0.001, 0.001)
            self.eyes_happy.append(hj)
        ball((0, -7.55 * s, 5.4 * s), (0.75 * s, 0.4 * s, 0.55 * s), P, self.head)               # nose
        O, Bk = m((0.93, 0.55, 0.2), 0.2, coat=0.7), m((0.12, 0.1, 0.1), 0.2, coat=0.7)
        ball((4.6 * s, -3.6 * s, 9.6 * s), (3.0 * s, 2.6 * s, 2.0 * s), O, self.head)            # calico patches
        ball((-4.9 * s, -2.2 * s, 10.0 * s), (2.4 * s, 2.4 * s, 1.6 * s), Bk, self.head)
        ball((5.5 * s, -4.5 * s, 9.0 * s), (2.0 * s, 2.0 * s, 1.6 * s), O, self.body)
        ball((-6.0 * s, 1.5 * s, 6.0 * s), (2.6 * s, 2.6 * s, 2.0 * s), Bk, self.body)
        for sd in (-1, 1):                                                                         # painted brows
            b = ball((sd * 3.2 * s, -6.6 * s, 9.3 * s), (1.1 * s, 0.15 * s, 0.22 * s), m((0.75, 0.1, 0.1), 0.3), self.head, seg=12)
            b.rotation_euler = (0, sd * 0.25, 0)
        self.mouth = joint(name + "_mouth", (0, -7.4 * s, 4.4 * s), self.head)
        for k in (-1, 1):
            b = ball((k * 0.55 * s, 0, 0), (0.7 * s, 0.2 * s, 0.18 * s), K, self.mouth)
            b.rotation_euler = (0, k * -0.45, 0)
        for sd in (-1, 1):                                                                         # whiskers
            for k in (-1, 0, 1):
                w = ball((sd * 7.4 * s, -6.2 * s, 5.0 * s + k * 0.7 * s), (2.6 * s, 0.1 * s, 0.1 * s), K, self.head, seg=12)
                w.rotation_euler = (0, sd * k * 0.15, sd * 0.25)
        # raised beckoning paw (figure's right = viewer's left = -x)
        self.paw_r = joint(name + "_paw_r", (-8.4 * s, -3.0 * s, 16.0 * s), self.body)
        ball((0, 0, 4.6 * s), (2.4 * s, 2.4 * s, 5.6 * s), W, self.paw_r)
        self.hand_r = joint(name + "_hand_r", (0, 0, 10.0 * s), self.paw_r)
        ball((0, -0.4 * s, 1.2 * s), (2.7 * s, 2.2 * s, 2.5 * s), W, self.hand_r)
        for k in (-1, 0, 1):
            ball((k * 0.85 * s, -2.4 * s, 1.0 * s), (0.4 * s, 0.15 * s, 0.4 * s), P, self.hand_r, seg=16)
        ball((0, -2.45 * s, -0.1 * s), (0.9 * s, 0.15 * s, 0.7 * s), P, self.hand_r, seg=16)
        self.paw_r.rotation_euler = (0, -0.3, 0)
        # left paw holding the gold koban
        self.paw_l = joint(name + "_paw_l", (6.4 * s, -2.0 * s, 14.0 * s), self.body)
        ball((-0.8 * s, -2.0 * s, -3.0 * s), (2.3 * s, 2.6 * s, 4.0 * s), W, self.paw_l)
        self.koban = joint(name + "_koban", (-2.6 * s, -6.5 * s, -5.0 * s), self.paw_l)
        ball((0, 0, 0), (2.6 * s, 0.45 * s, 4.0 * s), G, self.koban)
        for k in (-1, 0, 1):
            ball((0, -0.42 * s, k * 1.6 * s), (1.6 * s, 0.08 * s, 0.12 * s), m((0.85, 0.55, 0.15), 0.3, metal=1.0),
                 self.koban, seg=12)
        self.koban.rotation_euler = (0.1, 0, 0.15)

    # -------------------------------------------- poses
    def rest(self):
        self.body.rotation_euler = (0, 0, 0)
        self.head.rotation_euler = (0, 0, 0)
        self.body.location = (0, 0, 0)
        for leg in self.legs:
            leg.rotation_euler = (0, 0, 0)
        self.paw_r.rotation_euler = (0, -0.3, 0)
        self.hand_r.rotation_euler = (0, 0, 0)
        self.paw_l.rotation_euler = (0, 0, 0)
        self.happy(0.0)

    def beckon(self, t, speed=1.0, big=1.0):
        """The classic beckoning wave: the raised paw bends forward and back."""
        a = 0.5 + 0.5 * math.sin(t * 2 * math.pi * 0.9 * speed)
        self.hand_r.rotation_euler = (-1.3 * a * big, 0, 0)
        self.paw_r.rotation_euler = (-0.35 * a * big, -0.3, 0)

    def swipe(self, q):
        """Big downward swing of the raised paw (q 0..1)."""
        self.paw_r.rotation_euler = (-2.2 * q, -0.3 - 0.3 * q, 0)
        self.hand_r.rotation_euler = (-0.6 * q, 0, 0)

    def step(self, t, period=1.6):
        ph = (t % period) / period
        lift = max(0.0, math.sin(ph * 2 * math.pi))
        self.legs[0].rotation_euler = (-0.35 * lift, 0, 0)
        self.body.rotation_euler = (0, 0.04 * math.sin(ph * 2 * math.pi), 0)

    def awa_dance(self, t, amount=1.0):
        """Imitates Awa-odori: both paws up, sways side to side, lifts a leg on the beat."""
        ph = t * math.pi * 2.0
        sway = math.sin(ph)
        self.body.rotation_euler = (0, 0.12 * sway * amount, 0.06 * sway * amount)
        self.head.rotation_euler = (0, -0.08 * sway * amount, 0)
        self.paw_r.rotation_euler = (-0.2 * amount, -0.3 - 0.8 * amount + 0.25 * sway * amount, 0)
        self.hand_r.rotation_euler = (-0.6 * abs(sway) * amount, 0, 0)
        self.paw_l.rotation_euler = (0, 0.9 * amount + 0.25 * sway * amount, 0)
        up = max(0.0, sway)
        self.legs[0].rotation_euler = (-0.55 * up * amount, 0, 0)
        self.legs[1].rotation_euler = (-0.55 * max(0.0, -sway) * amount, 0, 0)
        self.body.location = (0, 0, 0.6 * self.s * abs(sway) * amount)

    def happy(self, k):
        """0 = open oval eyes, 1 = closed happy eyes + bigger smile."""
        for e in self.eyes_open:
            e.scale = (0.45 * self.s, 0.4 * self.s, 1.15 * self.s * max(0.02, 1 - k))
        for e in self.eyes_happy:
            v = max(0.001, k)
            e.scale = (v, v, v)
        self.mouth.scale = (1 + 0.6 * k, 1, 1 + 0.6 * k)


# ---------------------------------------------------------------- soft-toy people (reuse blocky poses)
from .blocky import Person as _BlockyPerson  # noqa: E402


class SoftPerson(_BlockyPerson):
    """Rounded figure with the same joints as blocky.Person, so stand / walk / awa_dance / look_up / wave work.
    outfit: casual / yukata (long robe, obi) / happi (short coat, shorts, hachimaki); hat='amigasa'."""

    def __init__(self, name, loc=(0, 0, 0), yaw=0.0, h=1.7, skin=0, hair=0, shirt=0, pants=0, outfit="casual",
                 accent=(0.85, 0.2, 0.2), hat=None, yukata=None):
        s = h / 1.7
        self.s = s
        self.root = joint(name, loc)
        self.root.rotation_euler = (0, 0, yaw)
        sk, hr = m(SKIN[skin % 3], 0.6, sss=0.15), m(HAIR[hair % 3], 0.5)
        sh = m(yukata or CLOTH[shirt % len(CLOTH)], 0.7)
        pa = m([(0.15, 0.15, 0.18), (0.3, 0.35, 0.5), (0.5, 0.42, 0.33)][pants % 3], 0.7)
        if outfit == "yukata":
            pa = sh
        if outfit == "happi":
            pa = m((0.12, 0.12, 0.15), 0.7)
        ac = m(accent, 0.5)
        self.hip = joint(name + "_hip", (0, 0, 0.86 * s), self.root)
        self.legs = []
        for sd in (-1, 1):
            j = joint(name + "_leg", (sd * 0.1 * s, 0, 0), self.hip)
            ball((0, 0, -0.42 * s), (0.085 * s, 0.09 * s, 0.42 * s), pa, j, seg=20)
            ball((0, -0.05 * s, -0.84 * s), (0.08 * s, 0.13 * s, 0.05 * s), m((0.15, 0.1, 0.08), 0.6), j, seg=16)
            self.legs.append(j)
        self.chest = joint(name + "_chest", (0, 0, 0), self.hip)
        if outfit == "yukata":                                                     # long robe over the legs
            ball((0, 0, -0.3 * s), (0.22 * s, 0.17 * s, 0.5 * s), sh, self.chest, seg=28)
        ball((0, 0, 0.33 * s), (0.22 * s, 0.15 * s, 0.36 * s), sh, self.chest, seg=28)
        if outfit in ("yukata", "happi"):
            torus((0, 0, 0.12 * s), 0.2 * s, 0.045 * s, ac, self.chest)           # obi / belt
        self.arms = []
        for sd in (-1, 1):
            j = joint(name + "_arm", (sd * 0.26 * s, 0, 0.58 * s), self.chest)
            ball((0, 0, -0.27 * s), (0.07 * s, 0.07 * s, 0.29 * s), sh, j, seg=20)
            ball((0, 0, -0.58 * s), 0.06 * s, sk, j, seg=16)
            self.arms.append(j)
        self.head = joint(name + "_head", (0, 0, 0.7 * s), self.chest)
        ball((0, 0, 0.17 * s), (0.15 * s, 0.15 * s, 0.17 * s), sk, self.head, seg=32)
        ball((0, 0.02 * s, 0.24 * s), (0.155 * s, 0.155 * s, 0.13 * s), hr, self.head, seg=28)
        self.eyes = [ball((sd * 0.05 * s, -0.142 * s, 0.18 * s), (0.016 * s, 0.01 * s, 0.024 * s), m((0.05, 0.04, 0.04), 0.3),
                          self.head, seg=12) for sd in (-1, 1)]
        if outfit == "happi":
            torus((0, 0, 0.27 * s), 0.15 * s, 0.025 * s, m((0.97, 0.97, 0.95), 0.6), self.head)  # hachimaki
        if hat == "amigasa":                                                       # folded straw hat
            hj = joint(name + "_hat", (0, -0.02 * s, 0.33 * s), self.head)
            straw = m((0.86, 0.72, 0.45), 0.8)
            for sd in (-1, 1):
                b = ball((sd * 0.13 * s, 0, 0.06 * s), (0.17 * s, 0.32 * s, 0.025 * s), straw, hj, seg=20)
                b.rotation_euler = (0, sd * 0.55, 0)
            ball((0, 0, 0.14 * s), (0.03 * s, 0.3 * s, 0.03 * s), m((0.7, 0.55, 0.3), 0.8), hj, seg=12)
        self.mouth = None


# ---------------------------------------------------------------- shotengai (shopping street)
SHOP_WALLS = [(0.92, 0.88, 0.8), (0.82, 0.78, 0.72), (0.88, 0.84, 0.76), (0.75, 0.62, 0.5), (0.9, 0.9, 0.86)]
AWNINGS = [(0.85, 0.25, 0.2), (0.2, 0.45, 0.7), (0.3, 0.6, 0.35), (0.95, 0.7, 0.25), (0.6, 0.35, 0.6),
           (0.92, 0.92, 0.9)]


def shotengai(length=90.0, width=8.0, seed=3):
    """Street along +y with two rows of two-storey shops, awnings, signboards, lanterns, potted plants and
    nobori flags (returned so scenes can blow them in the wind). Returns dict(nobori, vending, props)."""
    rnd = random.Random(seed)
    road = rbox((0, length / 2 - 10, -0.05), (width, length + 60, 0.1), m((0.55, 0.53, 0.5), 0.9), bevel=0)
    rbox((0, length / 2 - 10, -0.1), (400, 400, 0.1), m((0.42, 0.5, 0.34), 0.95), bevel=0)
    for k in range(0, int(length) + 40, 3):                                               # paving lines
        rbox((0, k - 10, 0.002), (width, 0.06, 0.004), m((0.62, 0.6, 0.56), 0.9), bevel=0)
    nobori, props = [], []
    for sx in (-1, 1):
        y = -10.0
        while y < length + 20:
            w = rnd.uniform(5.0, 7.0)
            h = rnd.uniform(6.5, 8.5)
            x = sx * (width / 2 + 3.2)
            wall = m(rnd.choice(SHOP_WALLS), 0.85)
            rbox((x, y, h / 2), (6.0, w - 0.3, h), wall, bevel=0.12)
            rbox((x - sx * 0.2, y, h + 0.35), (6.6, w, 0.7), m((0.3, 0.3, 0.34), 0.5), bevel=0.2)     # roof edge
            rbox((x - sx * 3.0, y, 1.4), (0.1, w - 1.4, 2.6), m((0.35, 0.45, 0.55), 0.15, emit=((0.9, 0.85, 0.7), 0.25)),
                 bevel=0.02)                                                                     # shop window
            aw = rbox((x - sx * 3.6, y, 3.1), (1.6, w - 0.5, 0.18), m(rnd.choice(AWNINGS), 0.6), bevel=0.06)
            aw.rotation_euler = (0, sx * 0.28, 0)
            rbox((x - sx * 3.05, y, 4.6), (0.12, w * 0.6, 1.0), m(rnd.choice(AWNINGS), 0.5), bevel=0.05)  # signboard
            for k in (-1, 1):                                                                    # lanterns
                ball((x - sx * 3.8, y + k * (w / 2 - 0.8), 3.9), (0.25, 0.25, 0.36), m((0.9, 0.2, 0.15), 0.5,
                                                                                         emit=((1.0, 0.5, 0.3), 0.6)))
            if rnd.random() < 0.6:                                                               # potted plant
                ball((x - sx * 3.6, y + w / 2 - 0.6, 0.35), (0.35, 0.35, 0.35), m((0.6, 0.35, 0.2), 0.7))
                ball((x - sx * 3.6, y + w / 2 - 0.6, 0.85), (0.45, 0.45, 0.4), m((0.25, 0.55, 0.25), 0.8))
            if rnd.random() < 0.7:                                                               # nobori flag
                j = joint("nobori", (x - sx * 4.2, y - w / 2 + 0.6, 0))
                rbox((0, 0, 1.6), (0.05, 0.05, 3.2), m((0.4, 0.3, 0.2), 0.6), j, bevel=0)
                flag = joint("flag", (0, 0.02, 3.1), j)
                rbox((0, 0.3, -0.9), (0.03, 0.55, 1.8), m(rnd.choice(AWNINGS), 0.6), flag, bevel=0.02)
                nobori.append(flag)
            for _ in range(rnd.randint(1, 3)):                                                    # crates / products
                p = rbox((x - sx * 3.3 + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-w / 3, w / 3), 0.3),
                         (0.6, 0.5, 0.6), m(rnd.choice([(0.85, 0.55, 0.3), (0.95, 0.85, 0.4), (0.3, 0.6, 0.3),
                                                         (0.9, 0.35, 0.3)]), 0.6), bevel=0.06)
                props.append(p)
            y += w
    vending = joint("vending", (width / 2 - 0.4, 6.0, 0))
    rbox((0, 0, 0.95), (0.8, 1.0, 1.9), m((0.85, 0.15, 0.15), 0.35, coat=0.4), vending, bevel=0.06)
    rbox((-0.41, 0, 1.25), (0.02, 0.8, 0.8), m((0.95, 0.95, 0.9), 0.2, emit=((1.0, 0.98, 0.9), 1.2)), vending, bevel=0)
    for k in range(6):
        ball((-0.43, -0.3 + (k % 3) * 0.3, 1.1 + (k // 3) * 0.35), (0.02, 0.07, 0.12),
             m([(0.3, 0.6, 0.9), (0.9, 0.6, 0.2), (0.3, 0.7, 0.4)][k % 3], 0.3), vending, seg=12)
    return {"nobori": nobori, "vending": vending, "props": props, "road": road}


def far_hills(seed=8):
    rnd = random.Random(seed)
    for _ in range(8):
        ball((rnd.uniform(-160, 160), rnd.uniform(260, 340), -20), (rnd.uniform(60, 90), 40, rnd.uniform(35, 50)),
             m((0.4, 0.58, 0.45), 0.95), seg=24)


def blow_nobori(flags, t, strength):
    for i, f in enumerate(flags):
        f.rotation_euler = (0.15 * math.sin(t * 3 + i) * (0.3 + strength), 0, (0.6 + 0.4 * math.sin(t * 9 + i)) * strength)


def plaza(center, size=(64.0, 54.0)):
    """Paved square where the street opens out (room for the giant and a ring of dancers)."""
    rbox((center[0], center[1], -0.04), (size[0], size[1], 0.08), m((0.72, 0.68, 0.6), 0.85), bevel=0)
    for k in range(-5, 6):
        rbox((center[0] + k * size[0] / 11, center[1], -0.0), (0.08, size[1], 0.01), m((0.62, 0.58, 0.52), 0.9), bevel=0)


def town_blocks(skip, seed=21, extent=(-130, 130, -60, 190), step=9.0):
    """Rows of ordinary houses filling the view from above. skip(x, y) -> True keeps a spot empty."""
    rnd = random.Random(seed)
    walls = [m(c, 0.85) for c in ((0.9, 0.88, 0.82), (0.82, 0.8, 0.76), (0.86, 0.8, 0.7), (0.78, 0.82, 0.84))]
    roofs = [m(c, 0.5) for c in ((0.3, 0.32, 0.38), (0.5, 0.28, 0.22), (0.25, 0.35, 0.45), (0.38, 0.36, 0.34))]
    x0, x1, y0, y1 = extent
    y = y0
    while y < y1:
        x = x0
        while x < x1:
            if not skip(x, y) and rnd.random() < 0.85:
                w, d, h = rnd.uniform(6, 8), rnd.uniform(6, 8), rnd.uniform(5, 9)
                rbox((x, y, h / 2), (w, d, h), rnd.choice(walls), bevel=0.15)
                rbox((x, y, h + 0.5), (w + 0.6, d + 0.6, 1.0), rnd.choice(roofs), bevel=0.35)
            elif not skip(x, y):
                ball((x, y, 2.5), (3.0, 3.0, 2.8), m((0.28, 0.5, 0.28), 0.85), seg=20)          # a tree
            x += step
        y += step
