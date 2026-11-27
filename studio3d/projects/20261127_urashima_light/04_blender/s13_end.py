"""58.9-62.9 s: crane up over the sunset sea; the turtle swims away at an ordinary turtle's speed."""
from _common import aim, camera, ease, lerp, lerp3, math, sea

SECONDS = 4.0


def build(ctx):
    sea.sunset_beach()
    tu = sea.SeaTurtle((0, 5, -0.3), 1.0, yaw=math.pi)
    return {"t": tu, "cam": camera(30)}


def pose(ctx, h, t):
    tu = h["t"]
    tu.swim(t, 0.5)
    tu.root.location = (0.2 * math.sin(t * 0.8), lerp(5, 7, t / SECONDS), -0.3)
    k = ease(t / SECONDS)
    aim(h["cam"], lerp3((1.8, -6.5, 1.3), (1.0, -12, 7.5), k), lerp3((0, 5, 0.4), (0, 40, 3), k))
