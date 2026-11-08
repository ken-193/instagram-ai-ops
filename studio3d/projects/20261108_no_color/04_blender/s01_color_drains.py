"""s01: a colourful afternoon street; the countdown hits zero and every colour drains away. Slow dolly-in."""
import math

from _common import aim, camera, daylight, ease, shake
from studio3d.lib.blocky import Person, tree
from studio3d.lib.sets import town_street

SECONDS = 5.0


def build(ctx):
    town_street(seed=21)
    daylight(35, 200, 0.4, 3.2)
    ppl = [Person("a", (0.6, 6, 0), math.pi, 1.65, shirt=1, hair=1),
           Person("b", (1.5, 6.4, 0), math.pi, 1.15, shirt=3, pants=1),
           Person("c", (-1.2, 9.5, 0), math.pi * 0.8, 1.72, shirt=2, pants=1),
           Person("d", (-0.4, 12, 0), 0.0, 1.6, shirt=4, pants=2)]
    for x, y in ((3.0, 15.0), (-2.6, 11.0)):
        tree((x, y, 0), 3.2, col=(0.2, 0.62, 0.22))
    return {"ppl": ppl, "cam": camera(26)}


def pose(ctx, h, t):
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i)
    for p in h["ppl"][:2]:
        p.look_up(t, 0.35 * ease((t - 3.0) / 0.6))
    (sx, sy, sz), roll = shake(t, 0.008)
    q = ease(t / SECONDS)
    aim(h["cam"], (1.3 + sx, 1.2 + 1.4 * q + sy, 1.1 + sz), (0.7, 10, 1.6), roll=roll)
