"""s08: summer festival in daylight; fireworks burst but are almost invisible against the bright sky."""
import math
import random

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import box
from studio3d.lib.sets import crowd, festival_street

SECONDS = 5.0


def build(ctx):
    festival_street(lit=0.0)
    daylight(55, 200, 0.4, 3.2)
    people = crowd(12, ((-2.5, 2.5), (2, 9)), seed=31, outfits=("yukata", "yukata", "casual"), facing=3.14)
    rnd = random.Random(5)
    sparks = []
    for burst in range(2):
        cx, cz, t0 = (-3 + burst * 6, 26 + burst * 4, 0.8 + burst * 1.6)
        for i in range(60):
            d = (rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.3), rnd.uniform(-1, 1))
            o = box((cx, 40, cz), (0.22, 0.22, 0.22), (1.0, 0.9, 0.85), emit=((1.0, 0.75, 0.6), 1.2), bevel=0)
            sparks.append((o, (cx, 40, cz), d, t0))
    return {"people": people, "sparks": sparks, "cam": camera(24)}


def pose(ctx, h, t):
    for p in h["people"]:
        p.stand(t + p.phase)
        p.look_up(t, 0.6)
    for o, c, d, t0 in h["sparks"]:
        k = t - t0
        if k < 0 or k > 2.2:
            o.scale = (0, 0, 0)
            continue
        r = 7 * (1 - math.exp(-k * 2.5))
        o.location = (c[0] + d[0] * r, c[1] + d[1] * r, c[2] + d[2] * r - 1.2 * k * k)
        s = 0.11 * max(0, 1 - k / 2.2)
        o.scale = (s, s, s)
    q = ease(t / SECONDS)
    aim(h["cam"], (0.8, lerp(-4.5, -3.0, q), 1.7), (0, 30, lerp(10, 18, q)))
