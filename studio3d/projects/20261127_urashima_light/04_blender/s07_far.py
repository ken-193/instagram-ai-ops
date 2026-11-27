"""32.1-36.1 s: pull back from the Earth and turn: the palace floats beside a distant star, 150 light-years away."""
from _common import aim, camera, ease, lerp3, sea
from studio3d.lib.smooth import ball

SECONDS = 4.0
PAL = (-45.0, 150.0, 6.0)


def build(ctx):
    sea.deep_space()
    sea.earth((0, 0, 0), 10.0)
    ball((PAL[0] - 70, PAL[1] + 160, PAL[2] + 40), 22, sea.glow((1.0, 0.85, 0.6), 25.0), seg=48, name="far_star")
    ball((PAL[0], PAL[1] + 2, PAL[2] - 5), (24, 18, 6), sea.m((0.4, 0.36, 0.34), 0.8), seg=32, name="rock_island")
    sea.palace((PAL[0], PAL[1], PAL[2] - 0.5), 0.9)
    import bpy, math
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(55), 0, math.radians(-50)))
    bpy.context.object.data.energy = 3.0
    return {"cam": camera(28)}


def pose(ctx, h, t):
    k = ease(t / 2.6)
    loc = lerp3((6, -30, 3), (40, 40, 22), k)
    tgt = lerp3((0, 0, 0), (PAL[0], PAL[1], PAL[2] + 6), ease((t - 0.6) / 2.4))
    aim(h["cam"], loc, tgt)
