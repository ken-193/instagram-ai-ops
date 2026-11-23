"""s07: the ordinary town is now an endless land: a house is a mountain range. Wide crane."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import house
from studio3d.lib.sets import crowd, ground

SECONDS = 5.0


def build(ctx):
    ground(4000, (0.42, 0.55, 0.32))
    daylight(35, 200, 0.45, 3.0)
    house((0, 700, 0), 900, 700, 550, yaw=0.0)                                 # one house x170
    house((-1100, 1400, 0), 900, 700, 500, wall=(0.8, 0.84, 0.86), roof=(0.45, 0.25, 0.2))
    ppl = crowd(20, ((-6, 6), (0, 25)), seed=71, facing=0.0)
    return {"ppl": ppl, "cam": camera(24)}


def pose(ctx, h, t):
    for p in h["ppl"]:
        p.walk(t + p.phase, 0.8)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(1.0, 0.0, q), lerp(-6.0, -40.0, q), lerp(1.4, 30.0, q)), (0, lerp(30, 600, q), lerp(1.5, 200, q)))
