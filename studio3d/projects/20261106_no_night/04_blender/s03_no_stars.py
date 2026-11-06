"""s03: 2 am under a blue sky; a family in pajamas looks up for stars. Low orbit."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person
from studio3d.lib.sets import town_street

SECONDS = 5.0


def build(ctx):
    town_street(seed=8)
    daylight(60, 140, 0.35, 3.0)
    fam = [Person("dad", (-0.5, 10, 0), 0.3, 1.75, shirt=5, pants=1, hair=0),
           Person("mom", (0.4, 10.3, 0), -0.2, 1.62, shirt=4, pants=1, hair=1),
           Person("kid", (0.0, 9.6, 0), 0.0, 1.1, shirt=3, pants=1, hair=0)]
    return {"fam": fam, "cam": camera(24)}


def pose(ctx, h, t):
    for i, p in enumerate(h["fam"]):
        p.stand(t + i)
        p.look_up(t, 0.65)
    a = lerp(-2.2, -1.2, ease(t / SECONDS))
    aim(h["cam"], (math.cos(a) * 4.2, 10 + math.sin(a) * 4.2, 0.6), (0, 10, 2.2))
