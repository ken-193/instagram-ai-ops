"""s10: tiny dancers do Awa-odori around the giant sudachi; crane up (end card)."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person
from studio3d.lib.sets import ground
from studio3d.lib.worlds import giant_fruit

SECONDS = 5.0


def build(ctx):
    ground(2000, (0.62, 0.5, 0.33))
    daylight(50, 210, 0.45, 3.2)
    giant_fruit("sudachi", (0, 0, 3.1), r=3.4)
    ds = []
    for i in range(16):
        a = i * 2 * math.pi / 16
        onna = i % 2 == 0
        p = Person(f"d{i}", (math.cos(a) * 6.2, math.sin(a) * 6.2, 0), a + math.pi / 2, 1.6 if onna else 1.72,
                   shirt=7 if onna else 6, outfit="yukata" if onna else "happi",
                   accent=(0.85, 0.2, 0.25) if onna else (0.95, 0.75, 0.3), hat="straw" if onna else None)
        p.kind, p.phase, p.a = ("onna" if onna else "otoko"), i * 0.15, a
        ds.append(p)
    return {"ds": ds, "cam": camera(24)}


def pose(ctx, h, t):
    for p in h["ds"]:
        p.awa_dance(t + p.phase, p.kind)
        a = p.a + t * 0.12
        p.root.location = (math.cos(a) * 6.2, math.sin(a) * 6.2, 0)
        p.root.rotation_euler = (0, 0, a + math.pi)
    q = ease(t / SECONDS)
    aim(h["cam"], (0.0, lerp(-13.0, -16.0, q), lerp(2.0, 20.0, q)), (0, 0, lerp(2.5, 1.0, q)))
