"""5-11 s: the cat beckons with huge sweeps; the wind blows the nobori and goods away; one step and the
vending machine topples. Fast orbit around the cat."""
import math
import random

from _common import aim, camera, ease, lerp, shake
from _neko_common import CAT_Y, set_and_cat

SECONDS = 6.0


def build(ctx):
    st, neko = set_and_cat()
    rnd = random.Random(12)
    flyers = [{"o": p, "home": tuple(p.location), "t0": rnd.uniform(0.6, 2.5), "v": (rnd.uniform(-3, 3), rnd.uniform(-10, -5),
               rnd.uniform(4, 8)), "spin": rnd.uniform(4, 10)} for p in st["props"] if p.location.y > 20]
    return {"neko": neko, "st": st, "flyers": flyers, "cam": camera(18)}


def pose(ctx, h, t):
    from studio3d.lib.smooth import blow_nobori
    n = h["neko"]
    n.rest()
    n.beckon(t, speed=1.3, big=1.4)
    if 3.0 < t < 3.8:                                                   # one step
        n.legs[0].rotation_euler = (-0.5 * math.sin((t - 3.0) / 0.8 * math.pi), 0, 0)
    blow_nobori(h["st"]["nobori"], t, min(1.0, 0.3 + t / 3))
    for f in h["flyers"]:
        tau = t - f["t0"]
        if tau <= 0:
            f["o"].location = f["home"]
            continue
        x0, y0, z0 = f["home"]
        f["o"].location = (x0 + f["v"][0] * tau, y0 + f["v"][1] * tau, max(0.3, z0 + f["v"][2] * tau - 4.9 * tau * tau))
        f["o"].rotation_euler = (f["spin"] * tau, f["spin"] * 0.6 * tau, 0)
    tip = ease((t - 3.5) / 0.7)
    h["st"]["vending"].rotation_euler = (0, -1.45 * tip, 0)
    amp = 0.04 + (0.25 if 3.5 < t < 4.1 else 0.0)
    (sx, sy, sz), roll = shake(t, amp)
    a = lerp(-2.4, -0.6, ease(t / SECONDS))
    # keep the camera over the open plaza (52 < y < 112): a wider orbit passes through the town blocks
    r = lerp(27, 29, ease(t / SECONDS))
    aim(h["cam"], (math.cos(a) * r + sx, CAT_Y + math.sin(a) * r + sy, lerp(6, 22, ease(t / SECONDS)) + sz),
        (0, CAT_Y, 16), roll=roll)
