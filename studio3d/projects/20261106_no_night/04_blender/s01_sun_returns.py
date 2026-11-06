"""s01: dusk street; the setting sun climbs back up — night never comes. Low dolly-in, two people look up."""
import math

from _common import aim, camera, daylight, ease, lerp, set_sun, shake
from studio3d.lib.blocky import Person
from studio3d.lib.sets import town_street

SECONDS = 5.0


def build(ctx):
    town_street()
    sky, sun = daylight(3.0, 175, 0.35, 3.0)
    a = Person("mom", (0.8, 6, 0), math.pi, 1.65, skin=0, hair=1, shirt=1)
    b = Person("kid", (1.6, 6.3, 0), math.pi, 1.15, skin=0, hair=0, shirt=3)
    return {"sky": sky, "sun": sun, "a": a, "b": b, "cam": camera(26)}


def pose(ctx, h, t):
    q = ease((t - 1.6) / 2.2)                       # the sun turns back
    set_sun(h["sky"], h["sun"], lerp(3.0, 52.0, q), 175)
    for p in (h["a"], h["b"]):
        p.stand(t)
        p.look_up(t, 0.55 * ease((t - 2.0) / 0.8))
    (sx, sy, sz), roll = shake(t, 0.01)
    aim(h["cam"], (2.0 + sx, 2.0 + 1.2 * ease(t / SECONDS) + sy, 0.8 + sz), (0.9, 12, 2.2 + 1.6 * q), roll=roll)
