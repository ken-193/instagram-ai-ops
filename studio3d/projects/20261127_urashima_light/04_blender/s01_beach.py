"""0-6.5 s: sunset beach. Taro lets the turtle go; it crawls to the sea, turns and offers its back.
At 3.7 s the camera snaps onto the turtle's face (the "wait, in real life?" beat); it glances away."""
from _common import aim, camera, ease, lerp, lerp3, math, sea, shake, world_pos

SECONDS = 6.5


def build(ctx):
    sea.sunset_beach()
    t = sea.SeaTurtle((-0.9, -1.2, 0), 1.0, yaw=math.pi)
    tr = sea.Taro(loc=(1.1, -2.2, sea.sand_z(-2.2)), yaw=math.radians(125))
    return {"t": t, "tr": tr, "cam": camera(32)}


def pose(ctx, h, t):
    tu, tr = h["t"], h["tr"]
    tu.rest()
    # crawl toward the sea (+Y), then turn back to Taro and lower the front (an invitation)
    walk = ease(min(t, 2.4) / 2.4)
    y = lerp(-1.2, -0.3, walk)
    tu.root.location = (-0.9, y, sea.sand_z(y))
    if t < 2.4:
        tu.crawl(t)
    turn = ease((t - 2.4) / 0.9)
    tu.root.rotation_euler = (0, 0, lerp(math.pi, 0.83, turn))
    tu.body.rotation_euler = (lerp(0, -0.12, ease((t - 3.0) / 0.4)), 0, 0)
    tu.head.rotation_euler = (lerp(0, 0.15, turn), 0, 0)
    if t > 4.6:                                                   # shifty glance away
        tu.look(-ease((t - 4.6) / 0.25))
        tu.head.rotation_euler = (0.15, 0, -0.35 * ease((t - 4.8) / 0.5))
    if 5.6 < t < 5.8:
        tu.blink(math.sin((t - 5.6) / 0.2 * math.pi))
    # Taro: hands forward (letting go), then lowers them
    tr.stand(t)
    reach = 1 - ease((t - 1.2) / 0.8)
    for a in tr.arms:
        a.rotation_euler = (-0.9 * reach, 0, 0)
    if t < 3.7:
        k = ease(t / 3.7)
        aim(h["cam"], lerp3((2.4, -9.8, 1.4), (1.6, -7.6, 1.2), k), (-0.2, -1.1, 0.7), lens=32)
    else:                                                         # snap zoom onto the face, then hold
        hx, hy, hz = world_pos(tu.head)
        k = ease((t - 3.7) / 0.22)
        d = lerp(4.2, 2.7, k)
        (sx, sy, sz), roll = shake(t, 0.03 if t < 4.0 else 0.004)
        aim(h["cam"], (hx + 0.55 * d + sx, hy - 0.85 * d + sy, hz + 0.35 + sz), (hx + 0.15, hy - 0.3, hz),
            roll=roll, lens=lerp(32, 40, k))
