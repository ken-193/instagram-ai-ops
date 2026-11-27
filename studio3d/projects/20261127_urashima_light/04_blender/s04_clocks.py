"""16-20.8 s: calculation mode. Blueprint grid, two clocks: the Earth clock races, Taro's clock barely moves."""
from _common import aim, camera, ease, lerp, lerp3, sea

SECONDS = 5.0


def build(ctx):
    sea.blueprint()
    earth_c = sea.Clock((-1.9, 0, 2.4), 1.35, rim=(0.3, 0.85, 1.0), name="c_earth")
    taro_c = sea.Clock((1.9, 0, 2.4), 1.35, rim=(1.0, 0.62, 0.3), name="c_taro")
    return {"a": earth_c, "b": taro_c, "cam": camera(30)}


def pose(ctx, h, t):
    h["a"].set(t * 7.0)               # the world's time races
    h["b"].set(t * 0.07)              # Taro's time crawls (100x slower)
    k = ease(t / SECONDS)
    aim(h["cam"], lerp3((-1.2, -13.5, 3.4), (1.0, -12.5, 3.0), k), (lerp(-0.4, 0.4, k), 0, 2.3))
