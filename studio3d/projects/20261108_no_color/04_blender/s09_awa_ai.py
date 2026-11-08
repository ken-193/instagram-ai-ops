"""s09: Awa-odori in indigo — yukata and happi are the only colour on screen. Tracking."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person
from studio3d.lib.sets import crowd, festival_street

SECONDS = 5.0


def dancers():
    out = []
    for row in range(5):
        for col, x in enumerate((-1.2, 0.0, 1.2)):
            onna = (row + col) % 2 == 0
            p = Person(f"d{row}{col}", (x, 2 + row * 1.8, 0), 0.0, 1.6 if onna else 1.72, skin=row % 2, hair=0,
                       shirt=7, pants=0, outfit="yukata" if onna else "happi",
                       accent=(0.95, 0.95, 0.92), hat="straw" if onna else None)
            p.kind = "onna" if onna else "otoko"
            p.phase = row * 0.35 + col * 0.2
            out.append(p)
    return out


def build(ctx):
    festival_street(seed=14, lit=0.0)
    daylight(55, 210, 0.4, 3.2)
    ds = dancers()
    watchers = crowd(10, ((-3.2, -2.6), (0, 12)), seed=51, facing=-1.57) + crowd(10, ((2.6, 3.2), (0, 12)), seed=52, facing=1.57)
    return {"ds": ds, "watchers": watchers, "cam": camera(26)}


def pose(ctx, h, t):
    for p in h["ds"]:
        p.awa_dance(t + p.phase, p.kind)
    for p in h["watchers"]:
        p.wave(t + p.phase) if p.phase > 3 else p.stand(t + p.phase)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(-1.8, -1.4, q), lerp(-3.0, -1.0, q), 1.9), (0, lerp(4.0, 6.0, q), 1.2))
