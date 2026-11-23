"""s08: Tokushima — a sudachi as big as a two-storey house, tiny people gather. Orbit."""
import math

from _common import aim, camera, daylight, ease, lerp
from studio3d.lib.blocky import Person, house
from studio3d.lib.sets import ground
from studio3d.lib.worlds import giant_fruit

SECONDS = 5.0


def build(ctx):
    ground(2000, (0.62, 0.5, 0.33))
    daylight(45, 200, 0.45, 3.2)
    giant_fruit("sudachi", (0, 12, 3.1), r=3.4)                                # ~4 cm x 170 = ~6.8 m across
    house((-12, 14, 0), 6, 5, 6.0, yaw=0.3)                                    # a real-size house for comparison
    ppl = [Person(f"p{i}", (math.cos(a) * 5.4, 12 + math.sin(a) * 5.4, 0), a + math.pi / 2, 1.6 + 0.1 * (i % 2),
                  shirt=7 if i % 2 else 2, outfit="happi" if i % 3 == 0 else "casual", accent=(0.95, 0.95, 0.92))
           for i, a in enumerate([k * 0.55 - 2.6 for k in range(8)])]
    return {"ppl": ppl, "cam": camera(24)}


def pose(ctx, h, t):
    for i, p in enumerate(h["ppl"]):
        p.stand(t + i)
        p.look_up(t, 0.45)
    a = lerp(-1.9, -1.2, ease(t / SECONDS))
    aim(h["cam"], (math.cos(a) * 16, 12 + math.sin(a) * 16, 2.2), (0, 12, 3.2))
