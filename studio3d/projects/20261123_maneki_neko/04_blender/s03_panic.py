"""11-18 s: people run for it; the cat slams its paw down and leaves and confetti burst up; a moment of slow
motion; then the cat suddenly freezes. Hand-held tracking in front of the runners."""
import math

from _common import aim, camera, ease, lerp, shake
from _neko_common import CAT_Y, flying_bits, place_bits, set_and_cat, shopper
from studio3d.lib.core import slowmo

SECONDS = 7.0
SLOW = (2.6, 4.4, 0.25)


def build(ctx):
    st, neko = set_and_cat()
    ppl = [shopper(f"r{i}", ((i % 5) * 1.25 - 2.5, 30 + (i // 5) * 2.2 + (i % 2) * 0.7, 0), 0.0, i) for i in range(15)]
    bits = flying_bits(140, 5, [(0.95, 0.4, 0.35), (0.98, 0.8, 0.3), (0.35, 0.65, 0.35), (0.9, 0.55, 0.2),
                                (0.95, 0.95, 0.9), (0.4, 0.55, 0.85)])
    return {"neko": neko, "ppl": ppl, "bits": bits, "st": st, "cam": camera(24)}


def pose(ctx, h, t):
    from studio3d.lib.smooth import blow_nobori
    tau = slowmo(t, *SLOW)                                               # action time
    n = h["neko"]
    n.rest()
    frozen = t >= 6.0
    if not frozen:
        n.swipe(ease((tau - 1.6) / 0.7))
    else:
        n.swipe(1.0)
    blow_nobori(h["st"]["nobori"], tau if not frozen else 6.0, 1.0)
    for i, p in enumerate(h["ppl"]):
        tt = min(tau, 5.6)
        p.walk(tt + i * 0.2, 2.6)
        p.root.location.y = 30 + (i // 5) * 2.2 + (i % 2) * 0.7 - 5.2 * tt
        p.chest.rotation_euler = (0.25, 0, 0)
    place_bits(h["bits"], (0, CAT_Y - 14, 2.0), tau - 2.3)
    hit = 2.2 < tau < 2.8
    (sx, sy, sz), roll = shake(t, 0.08 if not hit else 0.3)
    cy = 30 - 5.2 * min(tau, 5.6) - 7.0
    aim(h["cam"], (1.2 + sx, cy + sy, 1.5 + sz), (0, cy + 30, lerp(4, 14, ease(t / SECONDS))), roll=roll)
