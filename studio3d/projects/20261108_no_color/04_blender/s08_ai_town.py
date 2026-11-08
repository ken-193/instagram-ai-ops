"""s08: Tokushima, an old merchant street with indigo noren — the only colour left in the world. Dolly forward."""
import math
import random

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, house, noren
from studio3d.lib.sets import ground

SECONDS = 5.0
AI = (0.09, 0.14, 0.4)


def build(ctx):
    rnd = random.Random(8)
    ground(200, (0.62, 0.58, 0.52))
    daylight(45, 200, 0.4, 3.2)
    for sx in (-1, 1):
        for k in range(7):
            y = k * 5.2
            house((sx * 5.0, y, 0), 4.6, 4.4, 3.6, wall=(0.92, 0.9, 0.84), roof=(0.22, 0.22, 0.25), yaw=sx * math.pi / 2)
            noren((sx * 2.75, y, 2.2), 1.8, yaw=-sx * math.pi / 2, col=AI)
    ppl = [Person(f"p{i}", (rnd.uniform(-1.5, 1.5), 4 + i * 3.2, 0), rnd.choice((0, math.pi)), rnd.uniform(1.5, 1.75),
                  shirt=7 if i % 2 == 0 else 5, pants=rnd.randrange(3), outfit="yukata" if i % 3 == 0 else "casual",
                  accent=(0.95, 0.95, 0.92)) for i in range(7)]
    return {"ppl": ppl, "cam": camera(26)}


def pose(ctx, h, t):
    for p in h["ppl"]:
        p.walk(t + p.root.location.y, 0.7)
    q = ease(t / SECONDS)
    aim(h["cam"], (0.0, lerp(-3.0, 2.0, q), 1.5), (lerp(-1.0, 0.8, q), 14, 1.8))
