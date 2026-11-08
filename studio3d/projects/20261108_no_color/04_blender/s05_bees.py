"""s05: a grey flower field — the bees still find the flowers. Macro, low."""
import math
import random

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import bee, flower
from studio3d.lib.sets import ground

SECONDS = 5.0
COLS = [(0.95, 0.3, 0.45), (0.98, 0.85, 0.2), (0.6, 0.3, 0.85), (0.98, 0.55, 0.15), (0.95, 0.95, 0.95)]


def build(ctx):
    ground(200, (0.35, 0.6, 0.28))
    daylight(55, 200, 0.4, 3.2)
    rnd = random.Random(5)
    for _ in range(260):
        x, y = rnd.uniform(-6, 6), rnd.uniform(-1, 14)
        if y < 0.6 and abs(x) < 2.0:                     # keep the lens clear
            continue
        flower((x, y, 0), rnd.choice(COLS), rnd.uniform(0.35, 0.7))
    bees = [bee(f"bee{i}", (0, 2, 0.8), s=0.2) for i in range(4)]
    return {"bees": bees, "cam": camera(30)}


def pose(ctx, h, t):
    for i, (b, wings) in enumerate(h["bees"]):
        a = t * (1.1 + 0.2 * i) + i * 1.6
        b.location = (math.cos(a) * (0.3 + 0.15 * i) + (i - 1.5) * 0.35, 1.2 + i * 0.35 + math.sin(a) * 0.25,
                      0.75 + 0.15 * math.sin(t * 3 + i))
        b.rotation_euler = (0, 0, a + math.pi / 2)
        for k, w in enumerate(wings):
            w.rotation_euler = (0, (1 if k else -1) * 0.6 * math.sin(t * 60 + i), 0)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(-0.2, 0.2, q), lerp(-0.8, -0.5, q), 0.8), (0, 2.0, 0.7))
