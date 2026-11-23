"""s03: a cat peers down at the tiny people: a monster. Low angle, slow push, blink."""
import math

from _common import aim, camera, daylight, ease, lerp
from _tiny_common import table_top
from studio3d.lib.blocky import Person, cat_head

SECONDS = 5.0


def build(ctx):
    table_top(col=(0.78, 0.74, 0.68))
    daylight(50, 160, 0.45, 3.0)
    cat, eyes = cat_head((0, 40, 11), s=1.0)
    ppl = [Person(f"p{i}", (x, 6 + abs(x) * 0.3, 0), math.pi, hh, shirt=s, pants=1) for i, (x, hh, s) in
           enumerate(((-1.4, 1.7, 0), (0.0, 1.62, 1), (1.4, 1.2, 3)))]
    return {"cat": cat, "eyes": eyes, "ppl": ppl, "cam": camera(18)}


def pose(ctx, h, t):
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i)
        p.look_up(t, 0.65)
        for a in p.arms:
            a.rotation_euler = (-0.4 * math.sin(t * 7 + i), 0, 0)
    blink = 1.0 - 0.9 * max(0.0, 1 - abs(t - 3.2) / 0.12)
    for e in h["eyes"]:
        e.scale = (1, 1, blink)
    h["cat"].location.y = 40 - 6.0 * ease(t / SECONDS)
    q = ease(t / SECONDS)
    aim(h["cam"], (0.8, lerp(-2.0, 0.5, q), 1.2), (0, 36, lerp(8, 11, q)))
