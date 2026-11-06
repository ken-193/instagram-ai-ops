"""s07: station square; the clock says midnight while the sun is overhead. Crane up from the crowd."""
from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.sets import crowd, plaza_clock

SECONDS = 5.0


def build(ctx):
    plaza_clock()
    daylight(80, 150, 0.4, 3.4)
    people = crowd(9, ((-4, 4), (-1, 3)), seed=21, facing=0.0)
    return {"people": people, "cam": camera(26)}


def pose(ctx, h, t):
    for p in h["people"]:
        p.stand(t + p.phase)
        p.look_up(t, 0.5)
        p.head.rotation_euler.y = 0.25                                            # head tilted: puzzled
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(2.5, 1.5, q), lerp(-9.0, -7.5, q), lerp(0.8, 4.5, q)), (0, 7.0, lerp(2.0, 7.4, q)))
