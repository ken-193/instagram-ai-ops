"""46.1-49.9 s: the night-side city lights of the Earth stream into the turtle: 12 years of humanity's energy."""
import random

from _common import aim, camera, ease, key_lights, lerp, lerp3, math, sea
from studio3d.lib.smooth import ball

SECONDS = 3.8
TURTLE = (13.0, -9.0, 7.0)


def build(ctx):
    sea.deep_space()
    sea.earth((0, 0, 0), 10.0, night=True)
    import bpy
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(100), 0, math.radians(160)))
    bpy.context.object.data.energy = 0.6
    tu = sea.SeaTurtle(TURTLE, 1.2, yaw=math.radians(-60))
    halo = ball(TURTLE, 1.0, sea.glow((1.0, 0.8, 0.45), 4.0, 0.3, key="halo"), seg=32, name="halo")
    key_lights(TURTLE, 0.8)
    rnd = random.Random(5)
    motes = []
    for i in range(220):
        th, ph = rnd.uniform(-1.2, 1.2), rnd.uniform(-1.0, 1.0)
        p = (10.2 * math.sin(th) * math.cos(ph), -10.2 * math.cos(th) * math.cos(ph), 10.2 * math.sin(ph))
        o = ball(p, 0.12, sea.glow((1.0, 0.8, 0.4), 12.0, key="mote"), seg=8, name="mote")
        motes.append((o, p, rnd.uniform(0, 1.0), rnd.uniform(0.7, 1.3)))
    return {"t": tu, "halo": halo, "motes": motes, "cam": camera(30)}


def pose(ctx, h, t):
    h["t"].swim(t, 0.5)
    for o, p, off, sp in h["motes"]:
        q = ((t * 0.55 * sp + off) % 1.0)
        bend = math.sin(q * math.pi) * 3.0
        o.location = (lerp(p[0], TURTLE[0], q ** 1.6), lerp(p[1], TURTLE[1], q ** 1.6) - bend, lerp(p[2], TURTLE[2], q ** 1.6) + bend)
        o.scale = (0.12 * (1 - 0.6 * q),) * 3
    g = 1.4 + 1.6 * ease(t / SECONDS) + 0.1 * math.sin(t * 20)
    h["halo"].scale = (g, g, g * 0.8)
    aim(h["cam"], lerp3((2, -36, 10), (6, -30, 12), ease(t / SECONDS)), (6, -4, 3))
