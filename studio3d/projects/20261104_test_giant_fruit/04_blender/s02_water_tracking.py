"""s02 (5s): water-level tracking shot in front of the fruit, slight hand-held shake, slow push-in."""
import math

from studio3d.lib.core import aim, camera, ease, lerp, shake
from studio3d.lib.worlds import drift_water, giant_fruit, japanese_river

SECONDS = 5.0


def build(ctx):
    world = japanese_river()
    fruit = giant_fruit("fruit", (0, 42, 2.6), r=3.5)
    cam = camera(lens=22)
    return {"world": world, "fruit": fruit, "cam": cam}


def pose(ctx, h, t):
    q = ease(t / SECONDS)
    fy = lerp(42, 35, t / SECONDS)
    h["fruit"].location = (0.5 * math.sin(t * 0.7 + 2), fy, 2.6 + 0.12 * math.sin(t * 2.2 + 1))
    h["fruit"].rotation_euler = (0.05 * math.sin(t * 1.3), 0.04, 1.0 + t * 0.2)
    drift_water(h["world"], t)
    dist = lerp(15, 10.5, q)
    (sx, sy, sz), roll = shake(t, 0.03)
    aim(h["cam"], (1.2 + sx, fy - dist + sy, 0.4 + 0.15 * q + sz * 0.3), (0, fy, 3.4), roll=roll)
