"""s04: hatchlings on a bright beach crawl in every direction except the sea. Ground-level tracking."""
import math
import random

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import turtle
from studio3d.lib.sets import beach

SECONDS = 5.0


def build(ctx):
    beach()
    daylight(65, 120, 0.4, 3.4)
    rnd = random.Random(4)
    ts = []
    for i in range(18):
        root, flips = turtle(f"t{i}", (rnd.uniform(-3, 3), rnd.uniform(0, 6), 0), rnd.uniform(0, 6.28), 0.32)
        ts.append((root, flips, root.location.copy(), root.rotation_euler.z, rnd.uniform(0, 6.28)))
    return {"ts": ts, "cam": camera(30)}


def pose(ctx, h, t):
    for root, flips, start, yaw, ph in h["ts"]:
        wob = yaw + 0.6 * math.sin(t * 0.8 + ph)                          # wandering, lost
        d = 0.18 * t
        root.location = (start.x - math.sin(wob) * d, start.y + math.cos(wob) * d * -1, 0)
        root.rotation_euler.z = wob
        for i, f in enumerate(flips):
            f.rotation_euler = (0, 0, 0.5 * math.sin(t * 7 + ph + i * math.pi))
    x = lerp(-1.5, 1.5, ease(t / SECONDS))
    aim(h["cam"], (x, 0.0, 0.75), (x * 0.4, 4.0, 0.0))
