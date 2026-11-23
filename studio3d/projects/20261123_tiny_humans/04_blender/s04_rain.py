"""s04: rain — each drop is a 1 m ball of water crashing around tiny people under a leaf. Low."""
import math
import random

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, box, raindrop
from studio3d.lib.sets import ground

SECONDS = 5.0


def build(ctx):
    ground(2000, (0.35, 0.5, 0.3))
    daylight(25, 200, 0.25, 1.4)
    leaf = box((0, 6, 3.2), (9, 6, 0.25), (0.25, 0.6, 0.25), bevel=0.4)
    leaf.rotation_euler = (0.12, 0, 0)
    box((0, 6.5, 1.6), (0.35, 0.35, 3.2), (0.3, 0.5, 0.25), bevel=0)                  # stem
    ppl = [Person(f"p{i}", (x, 6 + y, 0), math.pi, hh, shirt=s) for i, (x, y, hh, s) in
           enumerate(((-1.2, 0.2, 1.7, 1), (0.2, -0.3, 1.6, 4), (1.4, 0.4, 1.2, 3)))]
    rnd = random.Random(4)
    drops = []
    for i in range(26):
        r = rnd.uniform(0.35, 0.55)                                   # 4-6 mm x 170 / 2 = radius 0.34-0.51 m
        d = raindrop(f"d{i}", (0, 0, 0), r)
        drops.append({"o": d, "x": rnd.uniform(-6, 6), "y": rnd.uniform(1.5, 12), "phase": rnd.uniform(0, 1), "r": r})
    return {"ppl": ppl, "drops": drops, "cam": camera(22)}


def pose(ctx, h, t):
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i)
        p.look_up(t, 0.4)
    for d in h["drops"]:
        k = (t * 0.55 + d["phase"]) % 1.0
        z = lerp(12, d["r"], k)
        if abs(d["x"]) < 4.8 and 3 < d["y"] < 9:                          # stopped by the leaf
            z = max(z, 3.5 + d["r"])
        d["o"].location = (d["x"], d["y"], z)
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(-2.5, -1.5, q), -1.0, 1.0), (0, 6, lerp(2.0, 3.5, q)))
