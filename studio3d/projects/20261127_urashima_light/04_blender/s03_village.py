"""12-16 s: 300 years later. Taro in his indigo kimono stands in a present-day street; people walk past."""
from _common import aim, camera, ease, lerp3, math, sea

SECONDS = 4.0


def build(ctx):
    sea.modern_town()
    tr = sea.Taro(loc=(0.6, 2.0, 0), yaw=math.pi)
    walkers = [sea.SoftPerson("p%d" % i, (x, y, 0), yaw=yaw, shirt=i, pants=i % 3, hair=i % 2)
               for i, (x, y, yaw) in enumerate([(2.0, 14, math.pi * 0.0), (-1.4, 22, math.pi), (3.1, 30, 0.0)])]
    return {"tr": tr, "w": walkers, "cam": camera(30)}


def pose(ctx, h, t):
    tr = h["tr"]
    tr.stand(t)
    tr.head.rotation_euler = (0, 0, 0.45 * math.sin(t * 1.4))          # looking around, lost
    for i, p in enumerate(h["w"]):
        p.walk(t + i)
        x, y0, _ = p.root.location
        sgn = -1 if abs(p.root.rotation_euler.z) < 0.1 else 1
        p.root.location = (x, [14, 22, 30][i] + sgn * 1.3 * t, 0)
    k = ease(t / SECONDS)
    aim(h["cam"], lerp3((1.1, -3.2, 1.25), (1.6, -5.6, 1.7), k), (0.4, 9, 1.7))
