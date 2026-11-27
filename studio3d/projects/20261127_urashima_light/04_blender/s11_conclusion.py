"""49.9-53.4 s: silence. Back on the beach, the turtle sheepishly backs away from Taro. 「結論、乗るな亀」"""
from _common import aim, camera, ease, lerp, math, sea

SECONDS = 3.5


def build(ctx):
    sea.sunset_beach()
    tu = sea.SeaTurtle((-0.6, -0.9, 0), 1.0, yaw=0.83)
    tr = sea.Taro(loc=(1.2, -2.4, sea.sand_z(-2.4)), yaw=math.radians(125))
    return {"t": tu, "tr": tr, "cam": camera(40)}


def pose(ctx, h, t):
    tu, tr = h["t"], h["tr"]
    tu.rest()
    back = ease((t - 1.2) / 1.8)
    fx, fy = math.sin(0.83), -math.cos(0.83)                     # turtle forward (toward Taro)
    x, y = -0.6 - fx * 0.7 * back, -0.9 - fy * 0.7 * back
    tu.root.location = (x, y, sea.sand_z(y))
    if 1.2 < t < 3.0:
        tu.crawl(t, 0.6)
    tu.head.rotation_euler = (0.25, 0, -0.2)
    tu.look(-0.8)
    tr.stand(t)
    aim(h["cam"], (2.3, -7.6, 1.15), (0.1, -1.4, 0.65))
