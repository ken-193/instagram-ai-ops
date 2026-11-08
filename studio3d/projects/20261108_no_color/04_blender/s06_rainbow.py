"""s06: after the rain, a rainbow — now a grey arch. Two people point; tilt up."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, rainbow
from studio3d.lib.sets import town_street

SECONDS = 5.0


def build(ctx):
    town_street(seed=26)
    daylight(30, 230, 0.4, 3.0)
    rainbow((0, 45, -6), r=30, band=2.0)
    a = Person("a", (0.3, 5, 0), math.pi, 1.7, shirt=2)
    b = Person("b", (1.2, 5.2, 0), math.pi, 1.2, shirt=1, pants=1)
    return {"a": a, "b": b, "cam": camera(22)}


def pose(ctx, h, t):
    for p in (h["a"], h["b"]):
        p.stand(t)
        p.look_up(t, 0.6)
    h["b"].arms[1].rotation_euler = (-2.4, 0, 0)
    q = ease(t / SECONDS)
    aim(h["cam"], (2.6, -1.0, 1.0), (0.4, 30, lerp(8, 15, q)))
