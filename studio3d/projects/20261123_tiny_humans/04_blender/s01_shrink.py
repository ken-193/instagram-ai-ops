"""s01: an ordinary street; the countdown ends and everyone shrinks to almost nothing. Camera drops to the ground."""
import math

from _common import aim, camera, daylight, ease, lerp, shake
from studio3d.lib.blocky import Person
from studio3d.lib.sets import town_street

SECONDS = 5.0


def build(ctx):
    town_street(seed=31)
    daylight(40, 200, 0.4, 3.2)
    ppl = [Person("a", (0.4, 5.0, 0), math.pi, 1.7, shirt=1, hair=1),
           Person("b", (1.2, 5.3, 0), math.pi, 1.15, shirt=3, pants=1),
           Person("c", (-1.0, 8.0, 0), math.pi * 0.85, 1.72, shirt=2, pants=1)]
    return {"ppl": ppl, "cam": camera(26)}


def pose(ctx, h, t):
    k = ease((t - 3.0) / 0.9)
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i)
        s = lerp(1.0, 0.035, k)
        p.root.scale = (s, s, s)
    (sx, sy, sz), roll = shake(t, 0.012 if 3.0 < t < 3.9 else 0.004)
    aim(h["cam"], (1.6 + sx, lerp(0.5, 3.2, k) + sy, lerp(1.4, 0.12, k) + sz), (0.6, 5.6, lerp(1.3, 0.04, k)), roll=roll)
