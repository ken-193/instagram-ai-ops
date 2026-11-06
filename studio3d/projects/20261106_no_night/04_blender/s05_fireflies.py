"""s05: riverside in daylight; fireflies blink weakly and can't find each other. Slow push along the stream."""
import math
import random

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import box
from studio3d.lib.sets import forest_river

SECONDS = 5.0


def build(ctx):
    forest_river()
    daylight(58, 160, 0.35, 3.0)
    rnd = random.Random(2)
    flies = []
    for i in range(24):
        o = box((rnd.uniform(-2.5, 2.5), rnd.uniform(2, 10), rnd.uniform(0.4, 1.6)), (0.05, 0.08, 0.05),
                (0.95, 1.0, 0.5), emit=((0.9, 1.0, 0.4), 8.0), bevel=0)
        flies.append((o, o.location.copy(), rnd.uniform(0, 6.28)))
    return {"flies": flies, "cam": camera(32)}


def pose(ctx, h, t):
    for o, p0, ph in h["flies"]:
        o.location = (p0.x + 0.3 * math.sin(t * 0.9 + ph), p0.y + 0.2 * math.cos(t * 0.7 + ph),
                      p0.z + 0.15 * math.sin(t * 1.3 + ph))
        on = 1.0 if math.sin(t * 3 + ph) > 0.4 else 0.15
        o.scale = (0.045 * (0.6 + on), 0.06 * (0.6 + on), 0.045 * (0.6 + on))
    q = ease(t / SECONDS)
    aim(h["cam"], (1.2, lerp(-2.0, 0.5, q), 1.1), (0, 7, 0.9))
