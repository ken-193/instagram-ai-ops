"""s06: a tatami mat is a field bigger than a football pitch; tiny people walk across. High crane."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import tatami_floor
from studio3d.lib.sets import crowd

SECONDS = 5.0


def build(ctx):
    tatami_floor()
    daylight(50, 170, 0.45, 3.0)
    ppl = crowd(24, ((-12, 12), (-60, 20)), seed=61, facing=0.0)
    return {"ppl": ppl, "cam": camera(24)}


def pose(ctx, h, t):
    for p in h["ppl"]:
        p.walk(t + p.phase, 0.8)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(2.0, 8.0, q), lerp(-75, -95, q), lerp(2.0, 45.0, q)), (0, lerp(-50, 40, q), 0))
