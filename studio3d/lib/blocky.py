"""Blocky (box-built) characters and props with soft bevels — the 世界の仕様外 "toy diorama" look.

Characters are hierarchies of bevelled boxes parented to joint empties, so pose(t) only rotates joints.
Shared palettes keep every episode consistent.
"""
from __future__ import annotations

import math

import bpy

from .core import empty, mat

_MATS: dict = {}


def lin(rgb):
    """Colours in this kit are written as display (sRGB) values; Blender wants linear."""
    return tuple(c ** 2.2 for c in rgb)


def m(rgb, rough=0.75, emit=None, key=None):
    """Cached material per colour (fewer materials = faster renders)."""
    k = key or (tuple(round(c, 3) for c in rgb), rough, emit)
    if k not in _MATS:
        e = (lin(emit[0]), emit[1]) if emit else None
        _MATS[k] = mat("bm%d" % len(_MATS), lin(rgb), rough, emit=e)
    return _MATS[k]


def box(loc, size, col, parent=None, bevel=0.025, rough=0.75, emit=None, name="box"):
    bpy.ops.mesh.primitive_cube_add(location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = tuple(s / 2 for s in size)
    if bevel:
        b = o.modifiers.new("bev", "BEVEL")
        b.width, b.segments = min(bevel, min(size) * 0.3), 2
    o.data.materials.append(m(col, rough, emit))
    if parent is not None:
        o.parent = parent
    return o


def joint(name, loc, parent=None):
    j = empty(name, loc)
    j.empty_display_size = 0.05
    if parent is not None:
        j.parent = parent
    return j


# ---------------------------------------------------------------- palettes
SKIN = [(0.95, 0.76, 0.6), (0.82, 0.6, 0.42), (0.55, 0.36, 0.24)]
HAIR = [(0.08, 0.07, 0.07), (0.25, 0.15, 0.08), (0.75, 0.75, 0.75)]
CLOTH = [(0.2, 0.45, 0.75), (0.85, 0.35, 0.3), (0.3, 0.6, 0.35), (0.9, 0.75, 0.3), (0.45, 0.35, 0.6),
         (0.95, 0.95, 0.92), (0.15, 0.2, 0.35)]
PANTS = [(0.12, 0.12, 0.15), (0.25, 0.3, 0.45), (0.45, 0.38, 0.3)]


class Person:
    """Blocky person. kind: adult / child / elder; outfit: casual / yukata / happi / suit / pajama."""

    def __init__(self, name, loc=(0, 0, 0), yaw=0.0, h=1.7, skin=0, hair=0, shirt=0, pants=0, outfit="casual",
                 accent=(0.8, 0.2, 0.2), hat=None):
        s = h / 1.7
        self.s = s
        self.root = joint(name, loc)
        self.root.rotation_euler = (0, 0, yaw)
        sk, hr, sh, pa = SKIN[skin % 3], HAIR[hair % 3], CLOTH[shirt % len(CLOTH)], PANTS[pants % 3]
        if outfit in ("yukata", "happi"):
            pa = sh if outfit == "yukata" else (0.95, 0.95, 0.92)
        self.hip = joint(name + "_hip", (0, 0, 0.82 * s), self.root)
        self.legs = []
        for sd in (-1, 1):
            j = joint(name + "_leg", (sd * 0.1 * s, 0, 0), self.hip)
            box((0, 0, -0.38 * s), (0.17 * s, 0.2 * s, 0.78 * s), pa, j)
            box((0, -0.03 * s, -0.79 * s), (0.18 * s, 0.26 * s, 0.07 * s), (0.15, 0.12, 0.1), j)
            self.legs.append(j)
        self.chest = joint(name + "_chest", (0, 0, 0), self.hip)
        torso_len = 0.62 * s
        if outfit == "yukata":
            box((0, 0, -0.1 * s), (0.44 * s, 0.26 * s, 0.5 * s), sh, self.chest)
        box((0, 0, torso_len / 2), (0.46 * s, 0.26 * s, torso_len), sh, self.chest)
        if outfit in ("yukata", "happi"):
            box((0, 0, 0.14 * s), (0.48 * s, 0.28 * s, 0.08 * s), accent, self.chest)        # obi / belt
            box((0, -0.135 * s, 0.4 * s), (0.06 * s, 0.01 * s, 0.4 * s), (0.97, 0.97, 0.95), self.chest)
        if outfit == "suit":
            box((0, -0.135 * s, 0.42 * s), (0.08 * s, 0.01 * s, 0.32 * s), accent, self.chest)
        self.arms = []
        for sd in (-1, 1):
            j = joint(name + "_arm", (sd * 0.31 * s, 0, 0.56 * s), self.chest)
            box((0, 0, -0.27 * s), (0.15 * s, 0.17 * s, 0.56 * s), sh, j)
            box((0, 0, -0.6 * s), (0.13 * s, 0.14 * s, 0.12 * s), sk, j)
            self.arms.append(j)
        self.head = joint(name + "_head", (0, 0, torso_len), self.chest)
        box((0, 0, 0.21 * s), (0.4 * s, 0.38 * s, 0.4 * s), sk, self.head)
        box((0, 0.02 * s, 0.43 * s), (0.42 * s, 0.4 * s, 0.08 * s), hr, self.head)
        box((0, 0.17 * s, 0.26 * s), (0.42 * s, 0.08 * s, 0.34 * s), hr, self.head)
        if outfit == "happi":
            box((0, 0, 0.36 * s), (0.43 * s, 0.41 * s, 0.05 * s), (0.97, 0.97, 0.95), self.head)  # hachimaki
        if hat == "straw":
            hat_j = joint(name + "_hat", (0, 0, 0.47 * s), self.head)
            for sd in (-1, 1):
                b = box((sd * 0.14 * s, -0.02 * s, 0.03 * s), (0.34 * s, 0.5 * s, 0.04 * s), (0.85, 0.7, 0.42), hat_j)
                b.rotation_euler = (0, -sd * 0.55, 0)
        self.eyes = []
        for sd in (-1, 1):
            self.eyes.append(box((sd * 0.08 * s, -0.192 * s, 0.24 * s), (0.055 * s, 0.01 * s, 0.07 * s),
                                 (0.1, 0.08, 0.08), self.head, bevel=0))
        self.mouth = box((0, -0.192 * s, 0.12 * s), (0.1 * s, 0.01 * s, 0.025 * s), (0.45, 0.15, 0.15), self.head,
                         bevel=0)

    # -------------------------------------------------- poses (all pure functions of t)
    def stand(self, t, breathe=True):
        b = 0.012 * math.sin(t * 2.0) if breathe else 0
        self.chest.rotation_euler = (b, 0, 0)
        for a in self.arms:
            a.rotation_euler = (0, 0, 0)
        for leg in self.legs:
            leg.rotation_euler = (0, 0, 0)
        self.head.rotation_euler = (0, 0, 0.05 * math.sin(t * 0.7))

    def walk(self, t, speed=1.0):
        ph = t * 6.0 * speed
        for i, leg in enumerate(self.legs):
            leg.rotation_euler = (0.45 * math.sin(ph + i * math.pi), 0, 0)
        for i, a in enumerate(self.arms):
            a.rotation_euler = (-0.4 * math.sin(ph + i * math.pi), 0, 0)
        self.hip.location.z = 0.82 * self.s + 0.02 * abs(math.sin(ph))

    def awa_dance(self, t, kind="otoko"):
        """Awa-odori: same-side hand and foot forward together, hands raised."""
        ph = t * math.pi * 2.1
        side = 1 if math.sin(ph) >= 0 else -1
        amt = abs(math.sin(ph))
        for i, (a, leg) in enumerate(zip(self.arms, self.legs)):
            sd = -1 if i == 0 else 1
            fwd = sd == side
            raise_ = 2.5 if kind == "onna" else 2.0
            a.rotation_euler = (-0.5 * amt if fwd else 0.1, sd * -raise_, 0)
            leg.rotation_euler = (-0.5 * amt if fwd else 0.05, 0, sd * 0.12 if kind == "otoko" else 0)
        self.hip.location.z = (0.82 - (0.08 if kind == "otoko" else 0.02) - 0.03 * amt) * self.s

    def wave(self, t):
        self.stand(t)
        self.arms[1].rotation_euler = (0, 0, 0)
        self.arms[1].rotation_euler = (0, -2.6 + 0.35 * math.sin(t * 9), 0)

    def look_up(self, t, amount=0.5):
        self.head.rotation_euler = (amount, 0, 0)

    def shade_eyes(self, t):
        """Dazzled: hand over the eyes, squinting."""
        self.stand(t)
        self.arms[1].rotation_euler = (-2.2, -0.5, 0)
        for e in self.eyes:
            e.scale.z = 0.25
        self.head.rotation_euler = (0.25, 0, 0)

    def lie(self):
        self.root.rotation_euler = (math.pi / 2, 0, self.root.rotation_euler.z)


# ---------------------------------------------------------------- animals / props
def turtle(name, loc, yaw=0.0, size=0.18):
    root = joint(name, loc)
    root.rotation_euler = (0, 0, yaw)
    s = size
    box((0, 0, 0.35 * s), (0.9 * s, 1.1 * s, 0.4 * s), (0.25, 0.32, 0.2), root)
    box((0, -0.7 * s, 0.3 * s), (0.36 * s, 0.4 * s, 0.28 * s), (0.42, 0.45, 0.32), root)
    flips = []
    for sd in (-1, 1):
        j = joint(name + "_f", (sd * 0.45 * s, -0.25 * s, 0.25 * s), root)
        box((sd * 0.3 * s, 0, 0), (0.6 * s, 0.25 * s, 0.08 * s), (0.42, 0.45, 0.32), j)
        flips.append(j)
    return root, flips


def owl(name, loc, yaw=0.0, s=0.5):
    root = joint(name, loc)
    root.rotation_euler = (0, 0, yaw)
    body = (0.55, 0.42, 0.3)
    box((0, 0, 0.35 * s), (0.5 * s, 0.4 * s, 0.7 * s), body, root)
    box((0, 0, 0.82 * s), (0.52 * s, 0.44 * s, 0.4 * s), body, root)
    box((0, -0.2 * s, 0.32 * s), (0.36 * s, 0.05 * s, 0.45 * s), (0.85, 0.78, 0.62), root)
    eyes = []
    for sd in (-1, 1):
        box((sd * 0.12 * s, -0.22 * s, 0.85 * s), (0.16 * s, 0.04 * s, 0.16 * s), (0.98, 0.95, 0.85), root)
        eyes.append(box((sd * 0.12 * s, -0.245 * s, 0.85 * s), (0.08 * s, 0.02 * s, 0.08 * s), (0.08, 0.07, 0.06),
                        root, bevel=0))
        e = box((sd * 0.16 * s, 0, 1.06 * s), (0.08 * s, 0.08 * s, 0.14 * s), body, root)
        e.rotation_euler = (0, sd * 0.3, 0)
    box((0, -0.24 * s, 0.74 * s), (0.06 * s, 0.06 * s, 0.08 * s), (0.85, 0.6, 0.2), root)
    return root, eyes


def bat(name, loc, s=0.4):
    root = joint(name, loc)
    box((0, 0, 0), (0.18 * s, 0.16 * s, 0.32 * s), (0.18, 0.15, 0.16), root)
    wings = []
    for sd in (-1, 1):
        j = joint(name + "_w", (sd * 0.08 * s, 0, 0.05 * s), root)
        box((sd * 0.3 * s, 0, 0), (0.55 * s, 0.03 * s, 0.25 * s), (0.22, 0.18, 0.2), j)
        wings.append(j)
    return root, wings


def house(loc, w=4.0, d=4.0, h=3.0, wall=(0.86, 0.8, 0.7), roof=(0.25, 0.27, 0.32), yaw=0.0):
    root = joint("house", loc)
    root.rotation_euler = (0, 0, yaw)
    box((0, 0, h / 2), (w, d, h), wall, root, bevel=0.05)
    r = box((0, 0, h + 0.45), (w + 0.5, d + 0.5, 0.9), roof, root, bevel=0.2)
    for i in range(2):                                   # windows facing -y
        box((-w * 0.25 + i * w * 0.5, -d / 2 - 0.01, h * 0.55), (w * 0.22, 0.04, h * 0.28), (0.55, 0.7, 0.8), root,
            bevel=0, rough=0.15)
    box((0, -d / 2 - 0.01, 0.9), (0.8, 0.04, 1.8), (0.4, 0.28, 0.18), root, bevel=0)
    return root


def tree(loc, h=3.0, col=(0.2, 0.42, 0.18), trunk=(0.35, 0.24, 0.14)):
    root = joint("tree", loc)
    box((0, 0, h * 0.35), (0.3, 0.3, h * 0.7), trunk, root)
    for i, (dx, dy, dz, sz) in enumerate(((0, 0, 0.8, 1.6), (0.4, 0.2, 1.05, 1.0), (-0.35, -0.2, 1.0, 1.1))):
        box((dx, dy, h * dz), (sz, sz, sz * 0.85), tuple(c * (0.9 + 0.1 * i) for c in col), root, bevel=0.12)
    return root


def lantern(loc, parent=None, lit=0.0, col=(0.95, 0.35, 0.25)):
    emit = ((1.0, 0.75, 0.45), 6.0 * lit) if lit > 0 else None
    o = box(loc, (0.28, 0.28, 0.42), col if lit == 0 else (1.0, 0.85, 0.6), parent, bevel=0.1, emit=emit)
    box((loc[0], loc[1], loc[2] + 0.25), (0.2, 0.2, 0.06), (0.15, 0.12, 0.1), parent, bevel=0)
    return o
