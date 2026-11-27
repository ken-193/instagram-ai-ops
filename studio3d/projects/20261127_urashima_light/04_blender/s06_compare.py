"""28.1-32.1 s: on the blueprint floor: an ordinary turtle paddling (near lane) and a turtle-light streak
crossing again and again (far lane) — 700 million times faster."""
from _common import aim, camera, key_lights, lerp, math, sea
from studio3d.lib.smooth import ball

SECONDS = 4.0


def build(ctx):
    sea.blueprint()
    slow = sea.SeaTurtle((0.9, 0, 0), 0.8, yaw=-math.pi / 2)
    streak = ball((0, 6, 0.6), (9.0, 0.35, 0.35), sea.glow((0.75, 0.95, 1.0), 18.0), seg=24, name="streak")
    head = ball((0, 6, 0.6), (0.6, 0.6, 0.6), sea.glow((1.0, 1.0, 1.0), 30.0), seg=24, name="streak_head")
    key_lights((0, 0, 0.5), 0.6)
    return {"slow": slow, "streak": streak, "head": head, "cam": camera(35)}


def pose(ctx, h, t):
    sl = h["slow"]
    sl.swim(t, 0.5)
    sl.root.location = (lerp(0.9, 0.3, t / SECONDS), 0, 0.05)
    x = ((t * 55.0) % 70.0) - 35.0                                 # crosses the frame about every 1.3 s
    h["streak"].location = (x + 9.0, 6, 0.6)
    h["head"].location = (x, 6, 0.6)
    aim(h["cam"], (0, -8.5, 2.6), (0, 2.5, 0.9))
