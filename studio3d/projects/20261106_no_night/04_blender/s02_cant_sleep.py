"""s02: kid's bedroom at 9 pm flooded with sunlight; eyes wide open. Top-down dolly-in."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person
from studio3d.lib.sets import bedroom

SECONDS = 5.0


def build(ctx):
    daylight(50, 200, 0.25, 2.0)
    bedroom()
    kid = Person("kid", (-0.6, 0.35, 0.26), 0.0, 1.2, skin=0, hair=0, shirt=0, outfit="casual")
    kid.root.rotation_euler = (math.pi / 2 - 0.02, 0, math.pi)
    return {"kid": kid, "cam": camera(28)}


def pose(ctx, h, t):
    k = h["kid"]
    k.stand(t, breathe=False)
    k.head.rotation_euler = (0, 0, 0.35 * math.sin(t * 1.2))           # tossing and turning
    for e in k.eyes:
        e.scale.z = 1.0 if (t % 1.7) > 0.12 else 0.2                   # blinking, wide awake
    q = ease(t / SECONDS)
    aim(h["cam"], (lerp(1.8, 0.9, q), lerp(-2.6, -1.4, q), lerp(3.4, 2.4, q)), (-0.6, 0.6, 0.3))
