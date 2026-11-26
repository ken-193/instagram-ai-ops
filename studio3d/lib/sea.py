"""Sea / space kit for 「もしも浦島太郎を現実でやったら？」: a friendly sea turtle, Taro the fisherman,
a sunset beach with a glossy sea, and deep space with stretched starlight. Same joint idea as smooth.py:
pose(t) only moves / rotates joints, so every frame is a pure function of t.
"""
from __future__ import annotations

import math
import random

import bpy

from .core import empty
from .smooth import SoftPerson, ball, joint, lin, m

SHELL = (0.55, 0.36, 0.18)
SHELL_EDGE = (0.22, 0.13, 0.06)
TURTLE_SKIN = (0.52, 0.56, 0.36)
PLASTRON = (0.93, 0.82, 0.55)
INDIGO = (0.16, 0.24, 0.45)
SLOPE = math.radians(1.2)


def _shell_mat():
    """Carapace: amber scutes with darker seams (Voronoi distance-to-edge), clear coat."""
    mm = bpy.data.materials.new("turtle_shell")
    nt = mm.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1.0, 0.8, 2.5)
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 2.2
    vor.inputs["Randomness"].default_value = 0.35
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.0, (*lin(SHELL_EDGE), 1)
    e[1].position, e[1].color = 0.07, (*lin(SHELL), 1)
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 6.0
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 0.25
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.35
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], vor.inputs["Vector"])
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], mix.inputs["A"])
    nt.links.new(noise.outputs["Color"], mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    nt.links.new(vor.outputs["Distance"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = 0.4
    b.inputs["Coat Weight"].default_value = 0.6
    b.inputs["Coat Roughness"].default_value = 0.1
    return mm


class SeaTurtle:
    """Big friendly sea turtle (shell ~1.9 m long at s=1, big enough to carry a person). Faces -Y.
    Joints: root, head, flippers [front L, front R, back L, back R]. Eyelids for blinks / shifty looks."""

    def __init__(self, loc=(0, 0, 0), s=1.0, yaw=0.0, name="turtle"):
        self.s = s
        self.root = joint(name, loc)
        self.root.rotation_euler = (0, 0, yaw)
        self.body = joint(name + "_body", (0, 0, 0.42 * s), self.root)
        skin = m(TURTLE_SKIN, 0.55, sss=0.1, key="turtle_skin")
        ball((0, 0, 0.08 * s), (0.75 * s, 0.95 * s, 0.33 * s), _shell_mat(), self.body, seg=48, name="shell")
        ball((0, 0, -0.02 * s), (0.78 * s, 0.98 * s, 0.1 * s), m(SHELL_EDGE, 0.5, coat=0.3), self.body, seg=40,
             name="shell_rim")
        ball((0, 0, -0.1 * s), (0.66 * s, 0.86 * s, 0.14 * s), m(PLASTRON, 0.6), self.body, seg=32, name="plastron")
        # head on a neck joint
        self.head = joint(name + "_head", (0, -0.92 * s, 0.02 * s), self.body)
        ball((0, -0.12 * s, 0), (0.2 * s, 0.26 * s, 0.17 * s), skin, self.head, seg=24, name="neck")
        ball((0, -0.42 * s, 0.06 * s), (0.27 * s, 0.31 * s, 0.24 * s), skin, self.head, seg=32, name="head")
        ball((0, -0.58 * s, -0.04 * s), (0.2 * s, 0.14 * s, 0.1 * s), m((0.66, 0.64, 0.42), 0.5), self.head, seg=24,
             name="snout")
        for sd in (-1, 1):                                                         # gentle smile: two tilted strokes
            mo = ball((sd * 0.07 * s, -0.69 * s, -0.06 * s), (0.08 * s, 0.02 * s, 0.01 * s), m((0.22, 0.15, 0.08), 0.5),
                      self.head, seg=16, name="mouth")
            mo.rotation_euler = (0, sd * -0.35, sd * 0.25)
        self.eyes, self.irises = [], []
        for sd in (-1, 1):
            ej = joint(name + "_eye", (sd * 0.16 * s, -0.6 * s, 0.17 * s), self.head)
            ej.rotation_euler = (0, 0, sd * -0.35)                                 # eyes look a little forward
            ball((0, 0, 0), 0.1 * s, m((0.98, 0.97, 0.94), 0.25), ej, seg=24, name="eye_white")
            ir = ball((0, -0.075 * s, 0.006 * s), (0.064 * s, 0.035 * s, 0.07 * s), m((0.1, 0.06, 0.03), 0.2),
                      ej, seg=20, name="iris")
            ball((-0.018 * s, -0.03 * s, 0.03 * s), 0.016 * s, m((1, 1, 1), 0.2, emit=((1, 1, 1), 2.0)), ir, seg=10,
                 name="glint")
            self.eyes.append(ej)
            self.irises.append(ir)
        # flippers: front long paddles, back short ones
        self.flippers = []
        for i, (x, y, L, w) in enumerate([(-0.66, -0.5, 0.95, 0.3), (0.66, -0.5, 0.95, 0.3),
                                          (-0.55, 0.72, 0.45, 0.22), (0.55, 0.72, 0.45, 0.22)]):
            sd = -1 if x < 0 else 1
            fj = joint(name + "_flip%d" % i, (x * s, y * s, -0.04 * s), self.body)
            f = ball((sd * L * 0.5 * s, 0.1 * L * s, 0), (L * 0.55 * s, w * s, 0.06 * s), skin, fj, seg=24, name="flipper")
            f.rotation_euler = (0, 0, sd * (0.45 if i < 2 else -0.6))
            self.flippers.append(fj)
        ball((0, 1.02 * s, -0.04 * s), (0.08 * s, 0.16 * s, 0.06 * s), skin, self.body, seg=16, name="tail")
        self.rest()

    def rest(self):
        self.head.rotation_euler = (0, 0, 0)
        for fj in self.flippers:
            fj.rotation_euler = (0, 0, 0)
        for ir in self.irises:
            ir.location.x = 0.0
        self.blink(0.0)

    def blink(self, k):
        """k=0 open, 1 closed (cartoon blink: the eye squashes flat)."""
        for ej in self.eyes:
            ej.scale = (1.0, 1.0, max(0.08, 1.0 - k))

    def look(self, x):
        """Move the irises sideways (x in -1..1) for shifty glances."""
        for ir in self.irises:
            ir.location.x = x * 0.03 * self.s

    def swim(self, t, speed=1.0, amount=1.0):
        """Front flippers sweep (power stroke), back flippers steer; head bobs a little."""
        p = t * speed * 2 * math.pi * 0.7
        for i, fj in enumerate(self.flippers):
            sd = -1 if i % 2 == 0 else 1
            if i < 2:
                fj.rotation_euler = (0, sd * 0.5 * math.sin(p) * amount, sd * 0.35 * math.cos(p) * amount)
            else:
                fj.rotation_euler = (0, sd * 0.25 * math.sin(p + 1.2) * amount, 0)
        self.head.rotation_euler = (0.06 * math.sin(p * 0.5) * amount, 0, 0)

    def crawl(self, t, amount=1.0):
        p = t * 2 * math.pi * 0.6
        for i, fj in enumerate(self.flippers):
            sd = -1 if i % 2 == 0 else 1
            ph = p + (math.pi if i in (1, 2) else 0)
            fj.rotation_euler = (0, sd * 0.2 * max(0, math.sin(ph)) * amount, sd * 0.4 * math.sin(ph) * amount)


class Taro(SoftPerson):
    """Taro the young fisherman: indigo short kimono, straw-rope belt, white hachimaki, bare shins."""

    def __init__(self, name="taro", loc=(0, 0, 0), yaw=0.0, h=1.65):
        super().__init__(name, loc, yaw, h=h, skin=0, hair=0, outfit="happi", accent=(0.82, 0.68, 0.4), yukata=INDIGO)

    def sit(self, amount=1.0):
        """Astride (on the turtle's shell): thighs forward, knees out."""
        self.hip.location.z = 0.86 * self.s - 0.78 * self.s * amount
        for sd, lg in zip((-1, 1), self.legs):
            lg.rotation_euler = (-1.35 * amount, sd * 0.45 * amount, 0)


# ---------------------------------------------------------------- environments
def sand_z(y):
    """Height of the beach at y (the sand rises gently toward -Y; the shoreline is at y ~ 0)."""
    return max(0.0, -y * math.tan(SLOPE))


def gradient_sky(bottom, mid, top, strength=1.0, stars=0.0, mid_at=0.08, top_at=0.4):
    """Vertical gradient world (horizon -> zenith). stars>0 adds tiny emissive dots (night / space)."""
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    nt = w.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.0, (*lin(bottom), 1)          # Generated Z of the world = view direction z
    el[1].position, el[1].color = top_at, (*lin(top), 1)
    mid_el = el.new(mid_at)
    mid_el.color = (*lin(mid), 1)
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    if stars:
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 420.0
        vor.feature = "F1"
        sr = nt.nodes.new("ShaderNodeValToRGB")
        se = sr.color_ramp.elements
        se[0].position, se[0].color = 0.0, (1, 1, 1, 1)
        se[1].position, se[1].color = 0.035, (0, 0, 0, 1)
        add = nt.nodes.new("ShaderNodeMix")
        add.data_type, add.blend_type = "RGBA", "ADD"
        add.inputs["Factor"].default_value = stars
        nt.links.new(tc.outputs["Generated"], vor.inputs["Vector"])
        nt.links.new(vor.outputs["Distance"], sr.inputs["Fac"])
        nt.links.new(ramp.outputs["Color"], add.inputs["A"])
        nt.links.new(sr.outputs["Color"], add.inputs["B"])
        nt.links.new(add.outputs["Result"], bg.inputs["Color"])
    else:
        nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    return ramp


def sunset_beach(seed=5):
    """Golden-hour beach along X: sand toward -Y (camera side), sea toward +Y, low warm sun behind the sea,
    a few rocks, pine trees on a headland, distant islands. Returns dict(sea, sun, sand)."""
    rnd = random.Random(seed)
    gradient_sky((1.0, 0.7, 0.36), (0.95, 0.62, 0.62), (0.2, 0.3, 0.62), strength=1.0, mid_at=0.08, top_at=0.5)
    vs = bpy.context.scene.view_settings
    vs.look, vs.exposure = "AgX - Punchy", 0.0
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(80), 0, math.radians(180)))
    sun = bpy.context.object
    sun.data.energy, sun.data.angle, sun.data.color = 3.4, math.radians(4), (1.0, 0.78, 0.58)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(40), 0, math.radians(20)))
    fill = bpy.context.object
    fill.data.energy, fill.data.color = 0.5, (0.55, 0.65, 1.0)
    # sun disc low over the sea
    ball((-30, 420, 9), 10, m((1, 0.8, 0.5), 0.5, emit=((1.0, 0.72, 0.42), 6.0)), name="sun_disc")
    # sand (slopes gently down into the sea)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, -80 * math.cos(SLOPE), 80 * math.sin(SLOPE)))
    sand = bpy.context.object
    sand.scale = (400, 200, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    sand.rotation_euler = (-SLOPE, 0, 0)
    sand.data.materials.append(m((0.95, 0.84, 0.66), 0.9, key="sand"))
    sm = sand.data.materials[0].node_tree
    noise = sm.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 60
    bp = sm.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.15
    sm.links.new(noise.outputs["Fac"], bp.inputs["Height"])
    sm.links.new(bp.outputs["Normal"], sm.nodes["Principled BSDF"].inputs["Normal"])
    # sea
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 300, 0.02))
    sea = bpy.context.object
    sea.name = "sea"
    sea.scale = (900, 600, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    water = bpy.data.materials.new("sea_water")
    b = water.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin((0.06, 0.22, 0.3)), 1)
    b.inputs["Roughness"].default_value = 0.16
    b.inputs["IOR"].default_value = 1.33
    nt = water.node_tree
    tco = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")                               # ripples in metres (object coords)
    nz.inputs["Scale"].default_value = 0.45
    nz.inputs["Detail"].default_value = 10.0
    nt.links.new(tco.outputs["Object"], nz.inputs["Vector"])
    bp2 = nt.nodes.new("ShaderNodeBump")
    bp2.inputs["Strength"].default_value = 0.6
    nt.links.new(nz.outputs["Fac"], bp2.inputs["Height"])
    nt.links.new(bp2.outputs["Normal"], b.inputs["Normal"])
    sea.data.materials.append(water)
    # rocks and a pine headland on the left, islands on the horizon
    rock = m((0.36, 0.32, 0.3), 0.8, key="rock")
    for _ in range(14):
        x = rnd.uniform(-60, -14)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, location=(x, rnd.uniform(-4, 14), 0))
        o = bpy.context.object
        o.scale = (rnd.uniform(1, 3), rnd.uniform(1, 3), rnd.uniform(0.6, 2.2))
        bpy.ops.object.shade_smooth()
        o.data.materials.append(rock)
    pine, trunk = m((0.12, 0.28, 0.16), 0.8, key="pine"), m((0.35, 0.22, 0.14), 0.8, key="trunk")
    for _ in range(9):
        x, y = rnd.uniform(-90, -45), rnd.uniform(5, 40)
        hgt = rnd.uniform(7, 12)
        ball((x, y, hgt / 2), (0.35, 0.35, hgt / 2), trunk, seg=10)
        for k in range(3):
            ball((x + rnd.uniform(-1, 1), y, hgt * (0.8 + 0.12 * k)), (3.2 - k * 0.7, 3.2 - k * 0.7, 1.0), pine, seg=16)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, location=(-70, 25, -6))
    head = bpy.context.object
    head.scale = (45, 30, 14)
    bpy.ops.object.shade_smooth()
    head.data.materials.append(m((0.3, 0.42, 0.22), 0.9, key="headland"))
    isl = m((0.48, 0.42, 0.52), 0.9, key="island")
    for x, w, hgt in [(120, 60, 14), (200, 40, 9), (-180, 70, 18)]:
        ball((x, 520, 0), (w, 20, hgt), isl, seg=24)
    return {"sea": sea, "sun": sun, "sand": sand}


def deep_space(seed=9, stretch=0.0):
    """Black space with stars; stretch>0 turns stars near the camera direction into streaks (near light speed).
    Returns dict(stars=[...]) of streak objects (scale them in pose)."""
    gradient_sky((0.01, 0.01, 0.03), (0.02, 0.02, 0.06), (0.0, 0.0, 0.02), strength=1.0, stars=0.9)
    rnd = random.Random(seed)
    streaks = []
    cols = [(0.7, 0.8, 1.0), (1.0, 0.95, 0.85), (0.6, 0.75, 1.0), (1.0, 0.8, 0.6)]
    for i in range(260):
        a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(6, 60)
        loc = (math.cos(a) * r, rnd.uniform(-200, 200), math.sin(a) * r)
        c = rnd.choice(cols)
        o = ball(loc, (0.06, 0.06, 0.06), m(c, 0.5, emit=(c, 30.0), key="star%d" % cols.index(c)), seg=8, name="streak")
        streaks.append(o)
    return {"stars": streaks}


def set_streaks(stars, stretch):
    """stretch 0..1 -> star dots become long light lines along Y."""
    for o in stars:
        o.scale = (0.06, 0.06 + stretch * 9.0, 0.06)


__all__ = ["SeaTurtle", "Taro", "sunset_beach", "sand_z", "deep_space", "set_streaks", "gradient_sky", "INDIGO", "empty"]
