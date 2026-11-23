"""27-30 s: hundreds of dancers and the cat dance together; the camera rockets up like a drone over a street
turned into one huge festival; the cat ends beaming with both paws up."""
import math
import random

from _common import aim, camera, ease, lerp
from _neko_common import CAT_Y, dance_templates, instance, set_and_cat

SECONDS = 3.0


def build(ctx):
    st, neko = set_and_cat()
    tm = dance_templates(4)
    rnd = random.Random(30)
    for i in range(320):                                                 # the street and the plaza round the cat
        if i < 200:
            x, y = rnd.uniform(-3.4, 3.4), rnd.uniform(-10, 62)
            yaw = math.pi
        else:
            a = rnd.uniform(0, 2 * math.pi)
            r = rnd.uniform(14, 24)
            x, y = math.cos(a) * r, CAT_Y + math.sin(a) * r
            yaw = a + math.pi / 2
        instance(tm[i % 4][1], (x, y, 0), yaw)
    return {"neko": neko, "tm": tm, "cam": camera(22)}


def pose(ctx, h, t):
    n = h["neko"]
    n.rest()
    for p, _ in h["tm"]:
        p.awa_dance(t + p.phase, p.kind)
    fin = ease((t - 2.2) / 0.6)
    n.awa_dance(t * (1 - fin) + 2.25 * fin, 1.0)                         # settles into the final pose
    n.paw_r.rotation_euler = (-0.2, lerp(n.paw_r.rotation_euler.y, -1.3, fin), 0)
    n.paw_l.rotation_euler = (0, lerp(n.paw_l.rotation_euler.y, 1.3, fin), 0)
    n.happy(ease((t - 0.4) / 0.8))
    k = ease(t / SECONDS)
    aim(h["cam"], (lerp(6, 8, k), lerp(CAT_Y - 34, CAT_Y - 70, k), lerp(14, 72, k)), (0, lerp(CAT_Y - 4, CAT_Y - 16, k), lerp(14, 0, k)))
