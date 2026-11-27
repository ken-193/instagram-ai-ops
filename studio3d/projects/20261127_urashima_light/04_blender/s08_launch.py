"""36.1-41.1 s: launch. 30 million G: Taro goes flat as a rice cracker (cartoon squash, no gore); camera shake."""
import random

from _common import aim, camera, ease, lerp, math, rider, sea, shake
from studio3d.lib.smooth import ball

SECONDS = 5.0
T0 = 1.6                                    # launch moment


def build(ctx):
    sea.sunset_beach()
    tu = sea.SeaTurtle((0, 6, -0.28), 1.0, yaw=math.pi)
    tr = rider(tu)
    aura = ball((0, 6, 0.3), 1.0, sea.glow((0.8, 0.95, 1.0), 3.0, 0.07, key="aura"), seg=32, name="aura")
    aura.scale = (0.001,) * 3
    aura.hide_render = True                    # a glow dome hid the gag; the spray and shake carry the impact
    rnd = random.Random(3)
    drops = []
    wm = sea.glow((0.85, 0.95, 1.0), 1.5, 0.7, key="spray")
    for i in range(60):
        d = ball((0, 6, 0), 0.03 + rnd.random() * 0.04, wm, seg=10, name="drop")
        drops.append((d, rnd.uniform(0, 2 * math.pi), rnd.uniform(2, 6), rnd.uniform(4, 9)))
    return {"t": tu, "tr": tr, "aura": aura, "drops": drops, "cam": camera(30)}


def pose(ctx, h, t):
    tu, tr = h["t"], h["tr"]
    tu.swim(t, 0.6 if t < T0 else 0.0)
    tu.blink(1.0 if T0 - 0.1 < t < T0 + 0.6 else 0.0)
    tr.flatten(ease((t - T0) / 0.08))
    tu.root.location = (0.06 * math.sin(t * 60) * (T0 < t < T0 + 0.8), 6, -0.28)
    g = ease((t - T0 + 0.3) / 0.3) * (1 - ease((t - T0 - 0.6) / 0.8)) * (1 + 0.15 * math.sin(t * 40))
    h["aura"].scale = (1.3 * g + 0.001, 1.5 * g + 0.001, 0.9 * g + 0.001)
    for d, a, v, up in h["drops"]:
        q = t - T0
        if q <= 0:
            d.location = (0, 6, -1)
            continue
        d.location = (math.cos(a) * v * q, 6 + math.sin(a) * v * q, max(-0.3, up * q - 4.9 * q * q))
    amp = 0.02 + (0.35 * max(0.0, 1 - (t - T0) / 0.9) if t > T0 else 0.0)
    (sx, sy, sz), roll = shake(t, amp)
    aim(h["cam"], (-4.2 + sx, 3.2 + sy, 1.6 + sz), (0, 6, lerp(0.75, 0.9, ease((t - T0 - 0.8) / 1.2))), roll=roll,
        lens=lerp(30, 42, ease((t - T0 - 0.8) / 1.2)))
