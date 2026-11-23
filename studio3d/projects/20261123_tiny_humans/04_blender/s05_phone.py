"""s05: a smartphone stands like a cinema screen; tiny people sit in front of it. Dolly back to reveal."""
import math

from _common import aim, camera, daylight, ease, lerp
from _tiny_common import table_top
from studio3d.lib.blocky import Person, smartphone

SECONDS = 5.0


def build(ctx):
    table_top(col=(0.85, 0.85, 0.86), wall=(0.75, 0.78, 0.82))
    daylight(45, 180, 0.35, 2.4)
    smartphone((0, 30, 0), 25.5)
    ppl = []
    for row in range(3):
        for k in range(5):
            ppl.append(Person(f"p{row}{k}", ((k - 2) * 1.4, 14 + row * 1.5, 0), 0.0, 1.5 + 0.1 * ((row + k) % 3),
                              shirt=(row * 5 + k) % 7, pants=k % 3, hair=row % 3))
    return {"ppl": ppl, "cam": camera(22)}


def pose(ctx, h, t):
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i * 0.3)
        p.look_up(t, 0.45)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(1.0, 2.0, q), lerp(9.0, 2.0, q), lerp(1.6, 3.5, q)), (0, 30, lerp(10, 12, q)))
