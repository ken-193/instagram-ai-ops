"""22-27 s: the dancers ring the cat; a lead dancer performs in front; the cat watches, tilts its head, then
copies: lifts a leg, raises both paws and sways. Super-low angle, then a crane up to overhead."""
import math

from _common import aim, camera, ease, lerp
from _neko_common import CAT_Y, dancer, set_and_cat

SECONDS = 5.0


def build(ctx):
    st, neko = set_and_cat()
    ring = []
    for i in range(36):
        a = i * 2 * math.pi / 36
        ring.append(dancer(f"r{i}", (math.cos(a) * 16, CAT_Y + math.sin(a) * 16, 0), a + math.pi / 2, i))
    lead = dancer("lead", (0, CAT_Y - 11, 0), math.pi, 0)
    return {"neko": neko, "ring": ring, "lead": lead, "cam": camera(20)}


def pose(ctx, h, t):
    n = h["neko"]
    n.rest()
    if t < 1.6:
        n.head.rotation_euler = (0, 0.18 * ease(t / 0.8), 0)             # curious head tilt
    amt = ease((t - 1.6) / 1.0)
    if amt > 0:
        n.awa_dance(t, amt)
    for p in h["ring"]:
        p.awa_dance(t + p.phase, p.kind)
    h["lead"].awa_dance(t * 1.1, "onna")
    up = ease((t - 2.4) / 2.6)
    aim(h["cam"], (lerp(2.0, 0.5, up), lerp(CAT_Y - 17, CAT_Y - 34, up), lerp(0.3, 48, up)),
        (0, CAT_Y - lerp(4, 0, up), lerp(14, 6, up)))
