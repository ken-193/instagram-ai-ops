"""53.4-58.9 s: the tamatebako. Smoke full of clock hands and stars; Taro gently becomes a white-haired old man."""
from _common import aim, camera, ease, lerp3, math, sea

SECONDS = 5.5


def build(ctx):
    sea.sunset_beach()
    tr = sea.Taro(loc=(0, -3, sea.sand_z(-3)), yaw=math.radians(10))
    box = sea.Tamatebako((0.05, -3.5, sea.sand_z(-3.5)), 1.0)
    return {"tr": tr, "box": box, "cam": camera(35)}


def pose(ctx, h, t):
    tr = h["tr"]
    tr.stand(t)
    for a in tr.arms:
        a.rotation_euler = (-0.75, 0, 0)
    h["box"].open(t, 0.6)
    tr.age(ease((t - 2.0) / 2.2))
    tr.head.rotation_euler = (-0.15 * ease((t - 0.6) / 0.6), 0, 0)
    k = ease(t / SECONDS)
    aim(h["cam"], lerp3((1.7, -8.2, 1.4), (1.0, -6.4, 1.35), k), (0, -3.2, 1.25))
