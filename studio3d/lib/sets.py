"""Blocky diorama sets (shared across episodes). Each builder returns a dict of things a scene may animate."""
from __future__ import annotations

import math
import random

import bpy

from .blocky import Person, box, house, joint, lantern, tree
from .core import area_light


def ground(size=200, col=(0.42, 0.55, 0.3), z=0.0):
    return box((0, 0, z - 0.05), (size, size, 0.1), col, bevel=0)


def town_street(seed=3, length=60):
    rnd = random.Random(seed)
    ground(200, (0.45, 0.55, 0.32))
    box((0, length / 2 - 10, 0.01), (6, length + 40, 0.04), (0.42, 0.42, 0.44), bevel=0)        # road
    for sx in (-1, 1):
        box((sx * 3.6, length / 2 - 10, 0.06), (1.2, length + 40, 0.12), (0.7, 0.68, 0.62), bevel=0.02)
        y = -6
        while y < length + 20:
            w = rnd.uniform(4, 6)
            house((sx * (6.5 + rnd.uniform(0, 1.5)), y, 0), w, rnd.uniform(4, 5), rnd.uniform(2.8, 4.2),
                  wall=rnd.choice([(0.88, 0.82, 0.72), (0.8, 0.84, 0.86), (0.9, 0.86, 0.78), (0.78, 0.72, 0.66)]),
                  roof=rnd.choice([(0.25, 0.27, 0.32), (0.45, 0.25, 0.2), (0.22, 0.32, 0.4)]), yaw=sx * math.pi / 2)
            y += w + rnd.uniform(1.0, 3.0)
        for k in range(0, length + 20, 12):                                                     # utility poles
            box((sx * 4.4, k, 3.0), (0.18, 0.18, 6.0), (0.55, 0.52, 0.48))
    for _ in range(8):
        tree((rnd.choice((-1, 1)) * rnd.uniform(12, 18), rnd.uniform(0, length), 0), rnd.uniform(3, 5))
    return {}


def bedroom():
    box((0, 0, -0.05), (8, 8, 0.1), (0.62, 0.48, 0.3), bevel=0)                                  # floor
    for i in range(6):                                                                           # tatami seams
        box((-3 + i * 1.2, 0, 0.003), (0.03, 7.6, 0.005), (0.5, 0.4, 0.26), bevel=0)
    box((0, 2.5, 1.5), (8, 0.15, 3), (0.86, 0.8, 0.7), bevel=0)                                  # back wall
    box((-2.6, 0, 1.5), (0.15, 8, 3), (0.86, 0.8, 0.7), bevel=0)                                 # side wall with window
    box((-2.52, 0.4, 1.6), (0.05, 1.6, 1.2), (1.0, 0.98, 0.9), bevel=0, emit=((1.0, 0.97, 0.88), 8.0))
    box((-0.6, 0.6, 0.12), (1.3, 2.1, 0.22), (0.92, 0.92, 0.95))                                 # futon
    box((-0.6, 1.45, 0.3), (0.7, 0.35, 0.16), (0.95, 0.95, 0.98))                                # pillow
    box((-0.6, -0.15, 0.27), (1.35, 0.8, 0.1), (0.95, 0.6, 0.55))                                # blanket (legs)
    box((1.6, 1.8, 0.45), (1.2, 0.6, 0.9), (0.55, 0.36, 0.22))                                   # chest of drawers
    box((1.6, 1.8, 1.1), (0.3, 0.3, 0.4), (0.95, 0.95, 0.9))                                     # clock
    area_light((-4.5, 0.4, 2.2), (90, 0, -90), 1800, 1.6)                                        # sun through window
    return {}


def plaza_clock(seed=5):
    rnd = random.Random(seed)
    ground(200, (0.72, 0.68, 0.6))
    box((0, 8, 4.5), (2.4, 2.4, 9), (0.82, 0.76, 0.66), bevel=0.06)                              # clock tower
    box((0, 8, 9.4), (3.0, 3.0, 0.8), (0.35, 0.25, 0.22), bevel=0.2)
    face = box((0, 6.78, 7.6), (1.7, 0.08, 1.7), (0.98, 0.97, 0.92), bevel=0.04)
    hands = joint("hands", (0, 6.7, 7.6))
    box((0, 0, 0.36), (0.1, 0.04, 0.72), (0.1, 0.1, 0.12), hands, bevel=0)                       # both hands at 12
    box((0, -0.01, 0.26), (0.14, 0.04, 0.52), (0.1, 0.1, 0.12), hands, bevel=0)
    for sx in (-1, 1):
        for k in range(3):
            house((sx * 12, 6 + k * 7, 0), 5, 5, rnd.uniform(3, 5), yaw=sx * math.pi / 2)
    for _ in range(6):
        tree((rnd.choice((-1, 1)) * rnd.uniform(5, 9), rnd.uniform(-3, 4), 0), rnd.uniform(2.5, 3.5))
    return {"face": face}


def beach():
    box((0, 10, -0.05), (200, 40, 0.1), (0.93, 0.78, 0.52), bevel=0)                              # sand
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 70, 0.02))
    sea = bpy.context.object
    sea.scale = (300, 80, 1)
    from .core import mat
    sea.data.materials.append(mat("sea", (0.05, 0.25, 0.32), 0.08, ior=1.33, bump=(0.4, 0.15, "noise")))
    for i in range(5):                                                                           # surf lines
        box((0, 30 + i * 0.9, 0.04), (300, 0.25, 0.02), (0.95, 0.97, 0.97), bevel=0)
    return {"sea": sea}


def forest_river(seed=7):
    rnd = random.Random(seed)
    ground(200, (0.3, 0.45, 0.22))
    box((0, 20, 0.0), (5, 80, 0.06), (0.25, 0.4, 0.45), bevel=0, rough=0.08)                     # stream
    for _ in range(60):
        x = rnd.choice((-1, 1)) * rnd.uniform(4, 30)
        tree((x, rnd.uniform(-5, 60), 0), rnd.uniform(3.5, 7), col=rnd.choice(
            [(0.16, 0.36, 0.14), (0.2, 0.42, 0.18), (0.13, 0.3, 0.12)]))
    for _ in range(30):
        box((rnd.choice((-1, 1)) * rnd.uniform(2.7, 4), rnd.uniform(-2, 40), 0.15), (0.6, 0.5, 0.3),
            (0.5, 0.5, 0.48), bevel=0.1)
    return {}


def festival_street(seed=9, lit=0.0, banners=True):
    """Shopping street with yatai stalls and lantern strings (lit=0: lanterns off, as in daylight)."""
    rnd = random.Random(seed)
    ground(200, (0.5, 0.48, 0.44))
    box((0, 20, 0.01), (7, 80, 0.04), (0.6, 0.56, 0.5), bevel=0)
    lanterns = []
    for sx in (-1, 1):
        for k in range(8):
            y = k * 5
            col = rnd.choice([(0.85, 0.3, 0.25), (0.25, 0.45, 0.75), (0.95, 0.75, 0.3), (0.3, 0.6, 0.35)])
            box((sx * 5, y, 1.2), (2.4, 2.0, 2.4), (0.75, 0.62, 0.45), bevel=0.04)               # stall
            box((sx * 5, y, 2.55), (2.8, 2.4, 0.3), col, bevel=0.06)                              # awning
            box((sx * 3.9, y, 1.1), (0.15, 2.0, 0.9), (0.95, 0.95, 0.92), bevel=0)                # counter
        for k in range(16):
            lanterns.append(lantern((sx * 3.6, k * 2.5, 3.4), lit=lit))
    for k in range(0, 40, 5):                                                                    # lantern rope posts
        for sx in (-1, 1):
            box((sx * 3.6, k, 1.8), (0.12, 0.12, 3.6), (0.4, 0.3, 0.2))
    for sx in (-1, 1):
        house((sx * 11, 30, 0), 6, 6, 4.5, yaw=sx * math.pi / 2)
    return {"lanterns": lanterns}


def crowd(n, area, seed=11, outfits=("casual", "yukata"), h=(1.45, 1.8), facing=0.0):
    rnd = random.Random(seed)
    (x0, x1), (y0, y1) = area
    people = []
    for i in range(n):
        p = Person(f"p{seed}_{i}", (rnd.uniform(x0, x1), rnd.uniform(y0, y1), 0), facing + rnd.uniform(-0.6, 0.6),
                   rnd.uniform(*h), skin=rnd.randrange(3), hair=rnd.randrange(3), shirt=rnd.randrange(7),
                   pants=rnd.randrange(3), outfit=rnd.choice(outfits),
                   accent=rnd.choice([(0.85, 0.2, 0.2), (0.95, 0.75, 0.25), (0.3, 0.55, 0.85)]))
        p.phase = rnd.uniform(0, 6.28)
        people.append(p)
    return people
