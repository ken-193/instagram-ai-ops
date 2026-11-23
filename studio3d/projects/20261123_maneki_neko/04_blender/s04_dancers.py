"""18-22 s: festival music from afar; the camera whips round to the near end of the street, where rows of
Awa-odori dancers in yukata and amigasa come dancing in. Tilt up from their feet to their faces."""
import math

from _common import aim, camera, ease, lerp
from _neko_common import CAT_Y, dancer, set_and_cat

SECONDS = 4.0


def build(ctx):
    st, neko = set_and_cat()
    ds = [dancer(f"d{i}", ((i % 4) * 1.5 - 2.25, -14 - (i // 4) * 1.9, 0), math.pi, i) for i in range(24)]
    return {"neko": neko, "ds": ds, "cam": camera(28)}


def pose(ctx, h, t):
    h["neko"].rest()
    h["neko"].swipe(1.0)
    for i, p in enumerate(h["ds"]):
        p.awa_dance(t + p.phase, p.kind)
        p.root.location.y = -14 - (i // 4) * 1.9 + 1.1 * t
    pan = ease(t / 1.2)                                                  # whip pan from the cat to the dancers
    tilt = ease((t - 1.0) / 2.6)
    tgt_far = (0, CAT_Y, 16)
    tgt_near = (0, -10 + 1.1 * t, lerp(0.15, 1.6, tilt))
    tx = lerp(tgt_far[0], tgt_near[0], pan)
    ty = lerp(tgt_far[1], tgt_near[1], pan)
    tz = lerp(tgt_far[2], tgt_near[2], pan)
    aim(h["cam"], (1.0, -3.0 + 0.6 * t, 1.0), (tx, ty, tz))
