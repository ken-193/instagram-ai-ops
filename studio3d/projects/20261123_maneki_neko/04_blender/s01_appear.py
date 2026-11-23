"""0-5 s: an ordinary afternoon in the shotengai; the ground shakes and a 30 m maneki-neko rises behind the far
rooftops. Camera starts at ground level and tilts / climbs up to the whole cat."""
import math

from _common import aim, camera, ease, lerp, shake
from _neko_common import CAT_Y, set_and_cat, shopper

SECONDS = 5.0


def build(ctx):
    st, neko = set_and_cat()
    ppl = [shopper(f"s{i}", ((-2.6 + (i % 5) * 1.3), 6 + i * 2.4, 0), math.pi if i % 3 else 0.0, i) for i in range(12)]
    return {"neko": neko, "ppl": ppl, "st": st, "cam": camera(22)}


def pose(ctx, h, t):
    rise = ease((t - 1.6) / 2.4)
    h["neko"].rest()
    h["neko"].root.location = (0, CAT_Y, lerp(-34, 0, rise))
    for i, p in enumerate(h["ppl"]):
        if t < 2.0:
            p.walk(t + i * 0.3, 0.7)
            p.root.location.y = 6 + i * 2.4 + (t * 0.5 if p.root.rotation_euler.z else -t * 0.5)
        else:
            p.stand(t + i)
            p.look_up(t, 0.5 * ease((t - 2.2) / 0.6))
    k = ease((t - 1.8) / 3.0)
    amp = 0.0 if t < 1.5 else (0.05 if t < 4.0 else 0.02)
    (sx, sy, sz), roll = shake(t, amp)
    aim(h["cam"], (1.0 + sx, lerp(-2.0, -6.0, k) + sy, lerp(0.35, 6.0, k) + sz),
        (0, lerp(20, CAT_Y, k), lerp(1.2, 18.0, k)), roll=roll)
