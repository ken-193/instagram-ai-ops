"""s10: crane up over the dancing street to the never-setting sun (end card)."""
from _common import aim, camera, daylight, ease, lerp
from s09_awa_day import dancers
from studio3d.lib.sets import crowd, festival_street

SECONDS = 5.0


def build(ctx):
    festival_street(seed=14, lit=0.0)
    daylight(60, 210, 0.4, 3.2)
    ds = dancers()
    watchers = crowd(14, ((-3.2, -2.6), (0, 14)), seed=43, facing=-1.57) + crowd(14, ((2.6, 3.2), (0, 14)), seed=44, facing=1.57)
    return {"ds": ds, "watchers": watchers, "cam": camera(24)}


def pose(ctx, h, t):
    for p in h["ds"]:
        p.awa_dance(t + p.phase, p.kind)
    for p in h["watchers"]:
        p.wave(t + p.phase) if p.phase > 3 else p.stand(t + p.phase)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(0.5, 0.0, q), lerp(-4.0, -9.0, q), lerp(1.6, 16.0, q)), (0, lerp(6, 10, q), lerp(1.5, 4.0, q)))
