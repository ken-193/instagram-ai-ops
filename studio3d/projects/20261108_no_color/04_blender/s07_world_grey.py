"""s07: crane up from a grey street until the whole town is grey."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.sets import crowd, town_street

SECONDS = 5.0


def build(ctx):
    town_street(seed=27, length=90)
    daylight(50, 180, 0.4, 3.2)
    ppl = crowd(18, ((-2.5, 2.5), (2, 30)), seed=71, facing=math.pi)
    return {"ppl": ppl, "cam": camera(24)}


def pose(ctx, h, t):
    for p in h["ppl"]:
        p.walk(t + p.phase, 0.8)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(1.0, 0.0, q), lerp(-2.0, -14.0, q), lerp(1.6, 30.0, q)), (0, lerp(10, 30, q), lerp(1.4, 0.0, q)))
