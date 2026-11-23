"""s09: one sudachi feeds the whole town: tiny people carry slices away. Tracking."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, box
from studio3d.lib.sets import ground
from studio3d.lib.worlds import giant_fruit

SECONDS = 5.0


def build(ctx):
    ground(2000, (0.62, 0.5, 0.33))
    daylight(45, 200, 0.45, 3.2)
    giant_fruit("sudachi", (2, 16, 3.1), r=3.4)
    carriers = []
    for i in range(10):
        p = Person(f"c{i}", (-3.0 + (i % 2) * 1.1, 9 - i * 1.6, 0), 0.0, 1.6, shirt=(i * 3) % 7, pants=i % 3)
        slab = box((0, -0.2, 2.0), (1.2, 0.8, 0.35), (0.75, 0.85, 0.35), p.root, bevel=0.1)   # a juicy slice
        p.slab = slab
        p.phase = i * 0.4
        carriers.append(p)
    return {"carriers": carriers, "cam": camera(24)}


def pose(ctx, h, t):
    for i, p in enumerate(h["carriers"]):
        p.walk(t + p.phase, 1.0)
        p.root.location.y = 9 - i * 1.6 - t * 1.1
        for a in p.arms:
            a.rotation_euler = (-2.9, 0, 0)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(2.5, 1.5, q), lerp(-6.0, -9.0, q), 1.8), (-2.5, lerp(4.0, 0.0, q), 1.6))
