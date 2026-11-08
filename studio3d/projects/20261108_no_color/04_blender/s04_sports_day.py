"""s04: school sports day tug-of-war — red team vs white team, but now nobody can tell. Side tracking."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, box, tree
from studio3d.lib.sets import ground

SECONDS = 5.0
RED, WHITE = (0.88, 0.15, 0.15), (0.97, 0.97, 0.95)


def build(ctx):
    ground(200, (0.72, 0.6, 0.42))
    daylight(50, 150, 0.4, 3.2)
    for k in range(10):
        tree((-14 + k * 3.2, 16, 0), 3.5, col=(0.25, 0.6, 0.25))
    box((0, 0, 0.75), (14, 0.08, 0.08), (0.85, 0.75, 0.5), bevel=0)                    # rope
    kids = []
    for side, cap in ((-1, RED), (1, WHITE)):
        for k in range(5):
            p = Person(f"k{side}{k}", (side * (1.2 + k * 1.1), 0.3 * (k % 2) - 0.15, 0), side * math.pi / 2, 1.2,
                       shirt=1 if side < 0 else 5, pants=1, outfit="happi", accent=cap)
            p.side = side
            kids.append(p)
    return {"kids": kids, "cam": camera(24)}


def pose(ctx, h, t):
    for i, p in enumerate(h["kids"]):
        p.stand(t + i)
        lean = 0.35 + 0.05 * math.sin(t * 6 + i)
        p.root.rotation_euler = (0, -p.side * lean * 0.0, p.side * math.pi / 2)
        p.chest.rotation_euler = (lean, 0, 0)
        for a in p.arms:
            a.rotation_euler = (-1.3, 0, 0)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(-7.5, -6.5, q), lerp(-3.4, -2.6, q), 1.5), (lerp(0.5, 1.5, q), 0, 0.8))
