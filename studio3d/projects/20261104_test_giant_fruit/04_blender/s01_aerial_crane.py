"""s01 (5s): high aerial view down the river, craning down and dollying forward; the giant fruit drifts in."""
import math

from studio3d.lib.core import aim, camera, ease, lerp, lerp3, shake
from studio3d.lib.worlds import drift_water, giant_fruit, japanese_river

SECONDS = 5.0


def build(ctx):
    world = japanese_river()
    fruit = giant_fruit("fruit", (0, 72, 2.6), r=3.5)
    cam = camera(lens=24)
    return {"world": world, "fruit": fruit, "cam": cam}


def pose(ctx, h, t):
    q = ease(t / SECONDS)
    fy = lerp(72, 64, t / SECONDS)
    h["fruit"].location = (0.6 * math.sin(t * 0.7), fy, 2.6 + 0.12 * math.sin(t * 2.2))
    h["fruit"].rotation_euler = (0.05 * math.sin(t * 1.3), 0.04, t * 0.2)
    drift_water(h["world"], t)
    loc = lerp3((6, 18, 38), (4, 30, 9), q)
    (sx, sy, sz), roll = shake(t, 0.05)
    aim(h["cam"], (loc[0] + sx, loc[1] + sy, loc[2] + sz), (0, fy + 4, 2.0), roll=roll)
