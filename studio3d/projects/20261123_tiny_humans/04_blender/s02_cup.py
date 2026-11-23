"""s02: tiny people on a dining table look up at a cup the size of a 5-storey building. Low tilt up."""
import math

from _common import aim, camera, daylight, ease, lerp
from _tiny_common import table_top
from studio3d.lib.blocky import Person, cup

SECONDS = 5.0


def build(ctx):
    table_top()
    daylight(45, 200, 0.45, 3.0)
    cup((0, 22, 0))
    ppl = [Person(f"p{i}", (x, 8 + i * 0.6, 0), math.pi + 0.2 * i, hh, shirt=s) for i, (x, hh, s) in
           enumerate(((-1.2, 1.7, 1), (0.3, 1.6, 4), (1.6, 1.15, 3)))]
    return {"ppl": ppl, "cam": camera(20)}


def pose(ctx, h, t):
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i)
        p.look_up(t, 0.7)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(2.5, 1.5, q), lerp(1.0, 2.0, q), 0.9), (0, 22, lerp(4, 14, q)))
