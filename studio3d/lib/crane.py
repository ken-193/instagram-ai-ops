"""Snow-country kit for 「もしも鶴の恩返しを、現実でやったら？」: a red-crowned crane (original rounded design),
a snowy village with thatched farmhouses, a weaving room with a loom and a backlit shoji (the famous silhouette),
falling snow, a bolt of cloth and loose feathers. Same joint idea as smooth.py: pose(t) only moves joints.
"""
from __future__ import annotations

import math
import random

import bpy

from .smooth import ball, cone, joint, lin, m, rbox, torus
from .sea import glow, gradient_sky

WHITE = (0.96, 0.96, 0.95)
BLACK = (0.08, 0.08, 0.09)
CROWN = (0.85, 0.12, 0.12)
BEAK = (0.62, 0.6, 0.45)
SKIN_PINK = (0.95, 0.72, 0.68)


class Crane:
    """Red-crowned crane, ~1.4 m tall at s=1, facing -Y. White body, black neck and tail plumes, red crown.
    Joints: root, body, neck, head, wings [L, R], legs [L, R]. plucked(k) swaps the body to bare pink skin."""

    def __init__(self, loc=(0, 0, 0), s=1.0, yaw=0.0, name="crane"):
        self.s = s
        self.root = joint(name, loc)
        self.root.rotation_euler = (0, 0, yaw)
        wh, bk = m(WHITE, 0.6, sss=0.1, key="crane_white"), m(BLACK, 0.5, key="crane_black")
        leg = m((0.2, 0.2, 0.22), 0.5, key="crane_leg")
        self.legs = []
        for sd in (-1, 1):
            lj = joint(name + "_leg", (sd * 0.09 * s, 0.02 * s, 0.72 * s), self.root)
            ball((0, 0, -0.36 * s), (0.025 * s, 0.025 * s, 0.36 * s), leg, lj, seg=10)
            ball((0, -0.06 * s, -0.71 * s), (0.03 * s, 0.1 * s, 0.012 * s), leg, lj, seg=10)
            self.legs.append(lj)
        self.body = joint(name + "_body", (0, 0, 0.82 * s), self.root)
        self.plumage = [ball((0, 0.02 * s, 0), (0.25 * s, 0.42 * s, 0.23 * s), wh, self.body, seg=32, name="body")]
        self.plumage.append(ball((0, 0.42 * s, 0.03 * s), (0.2 * s, 0.24 * s, 0.15 * s), bk, self.body, seg=24,
                                 name="tail_plume"))
        self.skin = ball((0, 0.02 * s, 0), (0.21 * s, 0.36 * s, 0.2 * s), m(SKIN_PINK, 0.6, sss=0.3, key="crane_skin"),
                         self.body, seg=28, name="bare")
        self.skin.hide_render = True
        self.wings = []
        for sd in (-1, 1):
            wj = joint(name + "_wing", (sd * 0.21 * s, -0.05 * s, 0.09 * s), self.body)
            w = ball((sd * 0.05 * s, 0.14 * s, 0), (0.07 * s, 0.4 * s, 0.17 * s), wh, wj, seg=24, name="wing")
            tip = ball((sd * 0.05 * s, 0.5 * s, -0.02 * s), (0.06 * s, 0.18 * s, 0.12 * s), bk, wj, seg=16,
                       name="wing_black")
            self.plumage += [w, tip]
            self.wings.append(wj)
        self.neck = joint(name + "_neck", (0, -0.32 * s, 0.1 * s), self.body)
        n1 = ball((0, -0.06 * s, 0.28 * s), (0.065 * s, 0.07 * s, 0.33 * s), bk, self.neck, seg=20, name="neck")
        n1.rotation_euler = (-0.3, 0, 0)
        self.head = joint(name + "_head", (0, -0.16 * s, 0.62 * s), self.neck)
        ball((0, 0, 0), (0.07 * s, 0.1 * s, 0.07 * s), wh, self.head, seg=20, name="head")
        ball((0, -0.02 * s, 0.05 * s), (0.04 * s, 0.05 * s, 0.02 * s), m(CROWN, 0.5, key="crown"), self.head, seg=14)
        ball((0, 0.03 * s, -0.04 * s), (0.055 * s, 0.07 * s, 0.05 * s), bk, self.head, seg=16)        # black cheek
        cone((0, -0.17 * s, -0.005 * s), 0.024 * s, 0.003 * s, 0.17 * s, m(BEAK, 0.45, key="beak"), self.head,
             rot=(math.pi / 2, 0, 0), verts=16)
        self.eyes = []
        for sd in (-1, 1):
            e = ball((sd * 0.05 * s, -0.04 * s, 0.012 * s), 0.014 * s, m((0.05, 0.04, 0.03), 0.2, key="crane_eye"),
                     self.head, seg=10)
            self.eyes.append(e)
        self.rest()

    def rest(self):
        for j in self.wings + self.legs:
            j.rotation_euler = (0, 0, 0)
        self.neck.rotation_euler = (0, 0, 0)
        self.head.rotation_euler = (0, 0, 0)
        self.body.rotation_euler = (0, 0, 0)

    def flap(self, t, speed=1.0, amount=1.0):
        a = math.sin(t * speed * 2 * math.pi * 1.2)
        for sd, wj in zip((-1, 1), self.wings):
            wj.rotation_euler = (0, sd * (-0.2 - 1.1 * a) * amount, sd * 0.15 * amount)

    def spread(self, k):
        """Wings open sideways (k=1) — the classic crane pose."""
        for sd, wj in zip((-1, 1), self.wings):
            wj.rotation_euler = (0, -sd * 1.3 * k, sd * 0.4 * k)

    def walk(self, t, speed=1.0):
        ph = t * 5 * speed
        for i, lj in enumerate(self.legs):
            lj.rotation_euler = (0.35 * math.sin(ph + i * math.pi), 0, 0)
        self.neck.rotation_euler = (0.08 * math.sin(ph * 2), 0, 0)

    def plucked(self, k):
        """0 = full plumage, 1 = bare (cartoon: a pink round body, a few feathers left on head and neck)."""
        bare = k > 0.5
        self.skin.hide_render = not bare
        for o in self.plumage:
            o.hide_render = bare
        if bare:
            self.skin.scale = (0.21 * self.s, 0.36 * self.s, 0.2 * self.s)

    def shiver(self, t, amount=1.0):
        self.body.rotation_euler = (0, 0.05 * math.sin(t * 40) * amount, 0)


def feather(loc, s=1.0, rgb=WHITE, parent=None, name="feather"):
    """A single contour feather (vane + quill), lying in the XY plane, pointing +Y."""
    j = joint(name, loc, parent)
    ball((0, 0, 0), (0.03 * s, 0.075 * s, 0.004 * s), m(rgb, 0.6, key="feather%s" % (rgb,)), j, seg=16)
    ball((0, -0.02 * s, 0.003 * s), (0.003 * s, 0.09 * s, 0.003 * s), m((0.85, 0.82, 0.75), 0.5, key="quill"), j, seg=8)
    return j


# ---------------------------------------------------------------- snow country
def snow_mat():
    return m((0.93, 0.95, 0.98), 0.55, sss=0.2, key="snow")


def minka(loc, yaw=0.0, s=1.0, lit=True, name="minka"):
    """Thatched farmhouse with a snow-laden roof; warm light in the windows when lit."""
    root = joint(name, loc)
    root.rotation_euler = (0, 0, yaw)
    wood, plaster = m((0.36, 0.24, 0.16), 0.7, key="wood"), m((0.85, 0.8, 0.7), 0.8, key="plaster")
    thatch = m((0.48, 0.38, 0.24), 0.9, key="thatch")
    rbox((0, 0, 1.4 * s), (8 * s, 6 * s, 2.8 * s), plaster, root, bevel=0.08)
    for x in (-3.9, -1.3, 1.3, 3.9):
        rbox((x * s, -3.02 * s, 1.4 * s), (0.25 * s, 0.1 * s, 2.8 * s), wood, root, bevel=0.03)
    roof = rbox((0, 0, 4.0 * s), (9.4 * s, 7.4 * s, 2.6 * s), thatch, root, bevel=1.2 * s)
    roof.scale = (1, 1, 1)
    rbox((0, 0, 5.15 * s), (8.6 * s, 6.4 * s, 0.9 * s), snow_mat(), root, bevel=0.45 * s)     # snow cap
    if lit:
        for x in (-2.6, 2.6):
            rbox((x * s, -3.03 * s, 1.5 * s), (1.6 * s, 0.05 * s, 1.0 * s), glow((1.0, 0.72, 0.42), 4.0, key="window"),
                 root, bevel=0)
    rbox((0, -3.03 * s, 1.1 * s), (1.4 * s, 0.06 * s, 2.0 * s), wood, root, bevel=0.03)
    return root


def snow_village(seed=7, dusk=True):
    """Snowy fields at dusk, a few farmhouses, snow-covered trees, low hills. Returns dict(flakes=[...])."""
    rnd = random.Random(seed)
    if dusk:
        gradient_sky((0.75, 0.68, 0.78), (0.45, 0.5, 0.7), (0.15, 0.2, 0.4), strength=1.0, mid_at=0.08, top_at=0.5)
    else:
        gradient_sky((0.85, 0.88, 0.92), (0.7, 0.78, 0.88), (0.45, 0.58, 0.8), strength=1.0, mid_at=0.08, top_at=0.5)
    vs = bpy.context.scene.view_settings
    vs.look, vs.exposure = "AgX - Punchy", 0.1
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(70), 0, math.radians(200)))
    sun = bpy.context.object
    sun.data.energy, sun.data.color, sun.data.angle = 2.2, (1.0, 0.85, 0.75), math.radians(5)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    g = bpy.context.object
    g.scale = (600, 600, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    g.data.materials.append(snow_mat())
    for i, (x, y, yaw) in enumerate([(-14, 22, 0.2), (12, 30, -0.3), (-30, 48, 0.1), (26, 60, -0.1)]):
        minka((x, y, 0), yaw, 1.0, lit=dusk, name="minka%d" % i)
    bark, needles = m((0.3, 0.22, 0.16), 0.8, key="bark"), m((0.15, 0.3, 0.2), 0.8, key="needles")
    for _ in range(40):
        x, y = rnd.uniform(-80, 80), rnd.uniform(15, 140)
        if abs(x) < 6 and y < 40:
            continue
        hgt = rnd.uniform(5, 10)
        ball((x, y, hgt * 0.3), (0.25, 0.25, hgt * 0.3), bark, seg=8)
        for k in range(3):
            r = (2.2 - 0.6 * k) * hgt / 8
            cone((x, y, hgt * (0.45 + 0.17 * k)), r, 0.1, hgt * 0.32, needles, verts=16)
            cone((x, y, hgt * (0.5 + 0.17 * k)), r * 0.8, 0.05, hgt * 0.2, snow_mat(), verts=16)
    hill = m((0.86, 0.88, 0.94), 0.8, key="hill")
    for _ in range(7):
        ball((rnd.uniform(-220, 220), rnd.uniform(220, 300), -30), (rnd.uniform(80, 120), 50, rnd.uniform(45, 70)),
             hill, seg=24)
    flakes = []
    fm = glow((1, 1, 1), 1.5, key="flake")
    for i in range(400):
        f = ball((rnd.uniform(-15, 15), rnd.uniform(-15, 25), rnd.uniform(0, 12)), 0.025, fm, seg=6, name="flake")
        flakes.append((f, tuple(f.location), rnd.uniform(0.6, 1.2), rnd.uniform(0, 6.28)))
    return {"flakes": flakes, "sun": sun}


def fall_snow(flakes, t, top=12.0):
    for f, (x, y, z), sp, ph in flakes:
        zz = (z - t * sp) % top
        f.location = (x + 0.3 * math.sin(t * 0.8 + ph), y, zz)


def weaving_room(seed=3):
    """Dim tatami room at night: a loom on the far side of a backlit shoji. A light behind the shoji makes a
    silhouette of whoever weaves. Returns dict(shoji, lamp, loom)."""
    gradient_sky((0.02, 0.02, 0.04), (0.02, 0.02, 0.04), (0.01, 0.01, 0.02), strength=1.0)
    bpy.context.scene.view_settings.exposure = 0.2
    tatami, wood = m((0.66, 0.6, 0.38), 0.85, key="tatami"), m((0.36, 0.24, 0.16), 0.7, key="wood")
    rbox((0, 0, -0.05), (12, 12, 0.1), tatami, bevel=0)
    for x in (-3, -1, 1, 3):
        rbox((x, 0, 0.002), (0.04, 12, 0.006), m((0.4, 0.35, 0.2), 0.8, key="tatami_line"), bevel=0)
    rbox((0, 6, 1.5), (12, 0.2, 3.0), m((0.55, 0.45, 0.35), 0.8, key="back_wall"), bevel=0)
    # shoji: translucent paper panels in a wooden lattice, across the room at y = 0
    paper = bpy.data.materials.new("shoji_paper")
    nt = paper.node_tree
    out = nt.nodes["Material Output"]
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.inputs["Color"].default_value = (*lin((1.0, 0.92, 0.78)), 1)
    df = nt.nodes.new("ShaderNodeBsdfDiffuse")
    df.inputs["Color"].default_value = (*lin((0.95, 0.92, 0.85)), 1)
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.75
    nt.links.new(df.outputs[0], mix.inputs[1])
    nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    shoji = rbox((0, 0, 1.25), (5.0, 0.02, 2.5), paper, bevel=0, name="shoji")
    for x in [-2.5 + i * 0.5 for i in range(11)]:
        rbox((x, -0.03, 1.25), (0.04, 0.04, 2.5), wood, bevel=0)
    for z in [0.05 + i * 0.35 for i in range(8)]:
        rbox((0, -0.03, z), (5.0, 0.04, 0.04), wood, bevel=0)
    # loom behind the shoji
    loom = joint("loom", (0, 1.4, 0))
    for x in (-0.7, 0.7):
        rbox((x, 0, 0.7), (0.08, 0.9, 0.08), wood, loom, bevel=0.01)
        rbox((x, -0.4, 0.6), (0.08, 0.08, 1.2), wood, loom, bevel=0.01)
        rbox((x, 0.4, 0.9), (0.08, 0.08, 1.8), wood, loom, bevel=0.01)
    rbox((0, -0.4, 0.8), (1.5, 0.12, 0.12), wood, loom, bevel=0.02)
    rbox((0, 0.4, 1.7), (1.5, 0.12, 0.12), wood, loom, bevel=0.02)
    bpy.ops.object.light_add(type="POINT", location=(0.4, 3.2, 1.5))
    lamp = bpy.context.object
    lamp.data.energy, lamp.data.color, lamp.data.shadow_soft_size = 400, (1.0, 0.75, 0.45), 0.05
    bpy.ops.object.light_add(type="POINT", location=(0, -4, 2.2))
    fill = bpy.context.object
    fill.data.energy, fill.data.color = 30, (0.6, 0.7, 1.0)
    return {"shoji": shoji, "lamp": lamp, "loom": loom}


def cloth_bolt(loc, length=12.0, width=0.37, unroll=1.0, name="bolt"):
    """A bolt of white crane-feather cloth with a subtle woven sheen; unroll 0..1 lays the strip out along +Y."""
    root = joint(name, loc)
    cl = bpy.data.materials.new(name + "_cloth")
    nt = cl.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin((0.97, 0.96, 0.93)), 1)
    b.inputs["Roughness"].default_value = 0.35
    b.inputs["Sheen Weight"].default_value = 0.8
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.inputs["Scale"].default_value = 60
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.15
    nt.links.new(wave.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    roll = ball((0, 0, width / 2), (0.09, 0.09, width / 2), cl, root, seg=24, name="roll")
    roll.rotation_euler = (0, math.pi / 2, 0)
    strip = rbox((0, length / 2, 0.003), (width, length, 0.004), cl, root, bevel=0, name="strip")
    return {"root": root, "roll": roll, "strip": strip, "length": length}


def set_unroll(bolt, k):
    L = max(0.001, bolt["length"] * k)
    bolt["strip"].scale = (1, L / bolt["length"], 1)
    bolt["strip"].location = (0, L / 2, 0.003)
    bolt["roll"].location = (0, L, 0.185)
    r = 0.09 * (1 - 0.6 * k) + 0.03
    bolt["roll"].scale = (r, r, 0.185)


__all__ = ["Crane", "feather", "minka", "snow_village", "fall_snow", "weaving_room", "cloth_bolt", "set_unroll",
           "snow_mat", "WHITE", "BLACK"]
