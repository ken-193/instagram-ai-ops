"""s06: owl squinting on a branch, a bat hanging still. Orbit around the owl."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import bat, box, owl
from studio3d.lib.sets import forest_river

SECONDS = 5.0


def build(ctx):
    forest_river(seed=12)
    daylight(62, 100, 0.35, 3.0)
    box((0.4, 0, 2.2), (2.6, 0.22, 0.22), (0.35, 0.24, 0.14))                     # branch
    box((-0.9, 0, 1.1), (0.35, 0.35, 2.2), (0.35, 0.24, 0.14))
    o, eyes = owl("owl", (0.2, 0, 2.31), 0.0, 0.85)
    b, wings = bat("bat", (1.2, 0, 1.85), 0.5)
    b.rotation_euler = (math.pi, 0, 0)                                            # upside down
    return {"owl": o, "eyes": eyes, "bat": b, "wings": wings, "cam": camera(35)}


def pose(ctx, h, t):
    for e in h["eyes"]:
        e.scale.z = 0.25 if (t % 2.4) > 0.3 else 0.05                             # squinting, sleepy
    h["owl"].rotation_euler.y = 0.08 * math.sin(t * 1.4)                          # nodding off
    for i, w in enumerate(h["wings"]):
        w.rotation_euler = (0, (-1 if i else 1) * 1.2, 0)                         # wrapped up
    a = lerp(-2.0, -1.0, ease(t / SECONDS))
    aim(h["cam"], (0.5 + math.cos(a) * 3.2, math.sin(a) * 3.2, 2.4), (0.5, 0, 2.6))
