"""s03: family dinner on a low table — the food is all grey. Top-down tilt."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, chabudai_meal
from studio3d.lib.sets import bedroom

SECONDS = 5.0


def build(ctx):
    bedroom()
    daylight(40, 200, 0.25, 1.5)
    chabudai_meal((0.6, -1.2, 0))
    fam = [Person("dad", (0.6, -2.3, 0), 0.0, 1.0, shirt=0, pants=1),
           Person("kid", (-0.65, -1.2, 0), -math.pi / 2, 0.75, shirt=3, pants=1),
           Person("mom", (1.85, -1.2, 0), math.pi / 2, 0.95, shirt=4, hair=1)]
    return {"fam": fam, "cam": camera(26)}


def pose(ctx, h, t):
    for i, p in enumerate(h["fam"]):
        p.stand(t + i)
        p.head.rotation_euler = (-0.45, 0, 0)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(0.2, 0.6, q), lerp(0.9, 0.5, q), lerp(1.9, 1.6, q)), (0.6, -1.5, 0.45))
