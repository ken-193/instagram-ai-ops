"""Sea / space kit for 「もしも浦島太郎を現実でやったら？」: a friendly sea turtle, Taro the fisherman,
a sunset beach with a glossy sea, and deep space with stretched starlight. Same joint idea as smooth.py:
pose(t) only moves / rotates joints, so every frame is a pure function of t.
"""
from __future__ import annotations

import math
import random

import bpy

from .core import empty
from .smooth import SoftPerson, ball, cone, far_hills, joint, lin, m, rbox, torus, town_blocks

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

    def age(self, k):
        """0 young -> 1 white-haired old man (hair turns white, a beard grows, back bends a little)."""
        if not hasattr(self, "_hair"):
            self._hair = bpy.data.materials.new("taro_hair")
            self._hair.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
            hair_src = m(__import__("studio3d.lib.smooth", fromlist=["HAIR"]).HAIR[0], 0.5)
            for o in self.head.children_recursive:
                if o.type == "MESH" and o.data.materials and o.data.materials[0] == hair_src:
                    o.data.materials[0] = self._hair
            self._beard = ball((0, -0.12 * self.s, 0.06 * self.s), (0.1 * self.s, 0.07 * self.s, 0.12 * self.s),
                               m((0.95, 0.95, 0.93), 0.7, key="beard"), self.head, seg=20, name="beard")
        c = [a + (b - a) * k for a, b in zip(lin((0.07, 0.06, 0.06)), lin((0.94, 0.94, 0.92)))]
        self._hair.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*c, 1)
        self._beard.scale = (0.1 * self.s * max(0.01, k), 0.07 * self.s * max(0.01, k), 0.12 * self.s * max(0.01, k))
        self.chest.rotation_euler.x = 0.25 * k

    def flatten(self, k):
        """Cartoon squash (k=1: pancake). No gore: the whole figure just goes flat and wide."""
        self.root.scale = (1 + 0.9 * k, 1 + 0.9 * k, max(0.08, 1 - 0.9 * k))

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


__all__ = ["Fish", "Clock", "ryugu", "modern_town", "blueprint", "earth", "water_mat", "Tamatebako", "SeaTurtle", "Taro", "sunset_beach", "sand_z", "deep_space", "set_streaks", "gradient_sky", "INDIGO", "empty"]


# ---------------------------------------------------------------- shared water material
def water_mat(key="sea_water2", base=(0.06, 0.22, 0.3), rough=0.16, ripple=0.45):
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    water = bpy.data.materials.new(key)
    nt = water.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(base), 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = 1.33
    tco = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = ripple
    nz.inputs["Detail"].default_value = 10.0
    nt.links.new(tco.outputs["Object"], nz.inputs["Vector"])
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.6
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return water


def glow(rgb, strength, alpha=1.0, key=None):
    """Emissive (optionally see-through) material for light shafts, smoke, sparks."""
    k = key or "glow%s%.2f%.2f" % (tuple(round(c, 2) for c in rgb), strength, alpha)
    if k in bpy.data.materials:
        return bpy.data.materials[k]
    mm = bpy.data.materials.new(k)
    b = mm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin(rgb), 1)
    b.inputs["Emission Color"].default_value = (*lin(rgb), 1)
    b.inputs["Emission Strength"].default_value = strength
    b.inputs["Alpha"].default_value = alpha
    return mm


# ---------------------------------------------------------------- Ryugu (undersea palace)
class Fish:
    """Simple round fish (sea bream red / flounder-ish / blue). Faces -Y; swim(t) wiggles the tail."""

    def __init__(self, loc, rgb, s=1.0, name="fish"):
        self.root = joint(name, loc)
        body = m(rgb, 0.35, coat=0.4)
        ball((0, 0, 0), (0.22 * s, 0.6 * s, 0.4 * s), body, self.root, seg=24)
        self.tail = joint(name + "_tail", (0, 0.55 * s, 0), self.root)
        t = ball((0, 0.22 * s, 0), (0.05 * s, 0.25 * s, 0.32 * s), body, self.tail, seg=16)
        t.rotation_euler = (0.0, 0, 0)
        ball((0, -0.05 * s, 0.38 * s), (0.04 * s, 0.35 * s, 0.12 * s), m(tuple(c * 0.8 for c in rgb), 0.4), self.root,
             seg=12)                                                                   # dorsal fin
        for sd in (-1, 1):
            ball((sd * 0.17 * s, -0.36 * s, 0.08 * s), 0.07 * s, m((0.98, 0.98, 0.96), 0.2), self.root, seg=12)
            ball((sd * 0.21 * s, -0.4 * s, 0.08 * s), 0.035 * s, m((0.05, 0.05, 0.05), 0.2), self.root, seg=10)

    def swim(self, t, phase=0.0):
        self.tail.rotation_euler = (0, 0, 0.45 * math.sin(t * 9 + phase))


def palace(loc=(0, 0, 0), s=1.0):
    """Ryugu palace (vermilion halls, stacked jade roofs, gold tips, glowing lanterns), centred on loc, facing -Y.
    Returns the lantern objects."""
    root = joint("palace", loc)
    root.scale = (s, s, s)
    verm, jade, gold, white = m((0.85, 0.2, 0.12), 0.45, coat=0.4), m((0.15, 0.55, 0.5), 0.4, coat=0.5), \
        m((0.95, 0.75, 0.3), 0.3, metal=0.8), m((0.95, 0.93, 0.88), 0.6)
    P = root
    rbox((0, 0, 0.6), (34, 24, 1.2), white, P, bevel=0.3)
    rbox((0, -14, 0.3), (10, 6, 0.6), white, P, bevel=0.2)
    lanterns = []
    for hx, hy, w, d, hgt, tiers in [(0, 2, 22, 14, 7.0, 3), (-14, -3, 8, 8, 5.0, 2), (14, -3, 8, 8, 5.0, 2)]:
        rbox((hx, hy, 1.2 + hgt / 2), (w, d, hgt), white, P, bevel=0.2)
        for px in [hx - w / 2 + 0.6 + i * (w - 1.2) / 5 for i in range(6)]:
            rbox((px, hy - d / 2 - 0.3, 1.2 + hgt / 2), (0.7, 0.7, hgt), verm, P, bevel=0.15)
        z = 1.2 + hgt
        for k in range(tiers):
            rw, rd = w + 4 - k * 4.5, d + 4 - k * 3.5
            rbox((hx, hy, z + 0.5), (rw, rd, 1.0), jade, P, bevel=0.45)
            for sx in (-1, 1):
                for sy in (-1, 1):
                    ball((hx + sx * rw / 2, hy + sy * rd / 2, z + 0.9), (0.5, 0.5, 0.35), gold, P, seg=12)
            if k < tiers - 1:
                rbox((hx, hy, z + 2.2), (rw - 5, rd - 4, 2.4), verm, P, bevel=0.2)
            z += 3.0
        ball((hx, hy, z + 0.2), (0.6, 0.6, 1.0), gold, P, seg=16)
        for sx in (-1, 1):
            L = ball((hx + sx * (w / 2 - 1.5), hy - d / 2 - 1.6, 3.2), (0.6, 0.6, 0.8), glow((1.0, 0.7, 0.35), 8.0), P,
                     seg=16, name="lantern")
            lanterns.append(L)
    return lanterns


def ryugu(seed=11):
    """Undersea palace: teal water light, sandy floor, coral, vermilion halls with jade roofs, glowing lanterns,
    light shafts from the surface. Palace centred at the origin, facing -Y. Returns dict(lanterns, shafts)."""
    rnd = random.Random(seed)
    gradient_sky((0.02, 0.2, 0.26), (0.05, 0.42, 0.5), (0.4, 0.8, 0.85), strength=1.0, mid_at=0.15, top_at=0.7)
    bpy.context.scene.view_settings.exposure = 0.3
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(15), 0, math.radians(30)))
    sun = bpy.context.object
    sun.data.energy, sun.data.color, sun.data.angle = 2.6, (0.7, 0.95, 1.0), math.radians(8)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    floor = bpy.context.object
    floor.scale = (600, 600, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    floor.data.materials.append(m((0.62, 0.7, 0.62), 0.9, key="seabed"))
    # mist: a big see-through teal shell hides the far floor edge
    lanterns = palace((0, 0, 0), 1.0)
    # coral and seaweed
    corals = [(0.98, 0.5, 0.55), (1.0, 0.65, 0.3), (0.75, 0.45, 0.85), (0.98, 0.85, 0.4)]
    for _ in range(70):
        a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(22, 90)
        x, y = math.cos(a) * r, math.sin(a) * r
        c = m(rnd.choice(corals), 0.6, key="coral%d" % rnd.randrange(4))
        for k in range(rnd.randint(2, 5)):
            ball((x + rnd.uniform(-1.5, 1.5), y + rnd.uniform(-1.5, 1.5), rnd.uniform(0.3, 2.2)),
                 (rnd.uniform(0.4, 1.0), rnd.uniform(0.4, 1.0), rnd.uniform(0.5, 1.6)), c, seg=14)
    weed = m((0.2, 0.5, 0.3), 0.7, key="weed")
    for _ in range(50):
        a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(20, 80)
        ball((math.cos(a) * r, math.sin(a) * r, 2.5), (0.25, 0.25, rnd.uniform(2, 4)), weed, seg=10)
    # light shafts from the surface
    shafts = []
    for i in range(7):
        sh = cone((rnd.uniform(-30, 30), rnd.uniform(-10, 40), 30), 1.5, 5.0, 60, glow((0.8, 1.0, 1.0), 0.6, 0.04,
                  key="shaft"), rot=(rnd.uniform(-0.2, 0.2), rnd.uniform(-0.25, 0.25), 0))
        shafts.append(sh)
    return {"lanterns": lanterns, "shafts": shafts}


# ---------------------------------------------------------------- 300 years later
def modern_town(seed=31):
    """Present-day Japanese street at dusk along Y: asphalt road, houses, utility poles and wires, a parked car,
    a lit vending machine, a convenience-style shop with a plain lit sign (no logos). Returns dict(road_y=..)."""
    rnd = random.Random(seed)
    gradient_sky((0.98, 0.72, 0.55), (0.62, 0.62, 0.78), (0.2, 0.28, 0.55), strength=1.0, mid_at=0.1, top_at=0.5)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(72), 0, math.radians(200)))
    sun = bpy.context.object
    sun.data.energy, sun.data.color = 2.4, (1.0, 0.8, 0.62)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 60, 0))
    g = bpy.context.object
    g.scale = (400, 400, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    g.data.materials.append(m((0.5, 0.52, 0.48), 0.9, key="ground"))
    rbox((0, 60, 0.03), (7, 300, 0.06), m((0.2, 0.2, 0.22), 0.8, key="asphalt"), bevel=0)
    for sx in (-1, 1):
        rbox((sx * 4.3, 60, 0.1), (1.6, 300, 0.2), m((0.7, 0.7, 0.68), 0.8, key="kerb"), bevel=0.05)
        rbox((sx * 0.0, 60, 0.065), (0.15, 300, 0.01), m((0.95, 0.95, 0.9), 0.6, key="line"), bevel=0)
    town_blocks(lambda x, y: abs(x) < 8, seed=seed, extent=(-60, 60, -10, 160), step=9.0)
    far_hills(seed)
    pole, wire = m((0.55, 0.55, 0.52), 0.7, key="pole"), m((0.08, 0.08, 0.08), 0.5, key="wire")
    for y in range(0, 160, 18):
        ball((5.6, y, 4.5), (0.14, 0.14, 4.5), pole, seg=10)
        rbox((5.6, y, 8.2), (1.6, 0.12, 0.12), pole, bevel=0)
    for dx in (-0.6, 0.0, 0.6):
        rbox((5.6 + dx, 80, 8.3), (0.03, 160, 0.03), wire, bevel=0)
    # parked car
    car = m((0.85, 0.86, 0.88), 0.25, coat=0.8, key="car")
    rbox((-2.2, 9, 0.75), (1.75, 4.2, 0.9), car, bevel=0.3)
    rbox((-2.2, 9.3, 1.45), (1.6, 2.4, 0.7), m((0.15, 0.2, 0.25), 0.1, key="glass"), bevel=0.25)
    for sy in (-1.3, 1.4):
        for sx in (-1, 1):
            torus((-2.2 + sx * 0.85, 9 + sy, 0.35), 0.24, 0.12, m((0.05, 0.05, 0.05), 0.7, key="tyre"),
                  rot=(0, math.pi / 2, 0))
    # vending machine and a shop
    rbox((5.4, 3.0, 0.95), (1.1, 0.8, 1.9), m((0.9, 0.9, 0.92), 0.4, key="vm"), bevel=0.06)
    rbox((5.4, 2.58, 1.1), (0.95, 0.05, 1.2), glow((0.9, 0.95, 1.0), 3.0, key="vmglow"), bevel=0)
    rbox((9.0, 14, 2.0), (6, 10, 4.0), m((0.95, 0.95, 0.93), 0.5, key="shop"), bevel=0.1)
    rbox((5.95, 14, 2.0), (0.1, 8, 2.6), glow((0.95, 0.97, 1.0), 2.5, key="shopwin"), bevel=0)
    rbox((5.9, 14, 3.6), (0.15, 9, 0.6), glow((0.3, 0.75, 0.55), 3.0, key="shopsign"), bevel=0)
    return {"sun": sun}


# ---------------------------------------------------------------- blueprint ("calculation mode")
def blueprint():
    """Dark navy void with a glowing cyan metre grid on the floor."""
    gradient_sky((0.02, 0.06, 0.16), (0.02, 0.05, 0.14), (0.01, 0.02, 0.08), strength=1.0)
    bpy.context.scene.view_settings.exposure = 0.0
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    fl = bpy.context.object
    fl.scale = (400, 400, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mm = bpy.data.materials.new("grid")
    nt = mm.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*lin((0.03, 0.08, 0.18)), 1)
    b.inputs["Roughness"].default_value = 0.35
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    lines = []
    for ax in ("X", "Y"):
        fr = nt.nodes.new("ShaderNodeMath")
        fr.operation = "PINGPONG"
        fr.inputs[1].default_value = 0.5
        nt.links.new(sep.outputs[ax], fr.inputs[0])
        lt = nt.nodes.new("ShaderNodeMath")
        lt.operation = "LESS_THAN"
        lt.inputs[1].default_value = 0.025
        nt.links.new(fr.outputs[0], lt.inputs[0])
        lines.append(lt)
    mx = nt.nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    nt.links.new(lines[0].outputs[0], mx.inputs[0])
    nt.links.new(lines[1].outputs[0], mx.inputs[1])
    em = nt.nodes.new("ShaderNodeMath")
    em.operation = "MULTIPLY"
    em.inputs[1].default_value = 3.0
    nt.links.new(mx.outputs[0], em.inputs[0])
    b.inputs["Emission Color"].default_value = (*lin((0.3, 0.85, 1.0)), 1)
    nt.links.new(em.outputs[0], b.inputs["Emission Strength"])
    fl.data.materials.append(mm)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(40), 0, math.radians(30)))
    bpy.context.object.data.energy = 1.2
    bpy.context.object.data.color = (0.6, 0.85, 1.0)
    return fl


class Clock:
    """Standing clock face (faces -Y): rim glows cyan, 12 ticks, hour + minute hands on joints."""

    def __init__(self, loc, r=2.0, rim=(0.3, 0.85, 1.0), name="clock"):
        self.root = joint(name, loc)
        f = ball((0, 0, 0), (r, 0.12, r), m((0.92, 0.95, 0.98), 0.4), self.root, seg=48)
        torus((0, -0.05, 0), r, 0.12 * r / 2, glow(rim, 4.0), self.root, rot=(math.pi / 2, 0, 0))
        for i in range(12):
            a = i / 12 * 2 * math.pi
            tk = rbox((math.sin(a) * r * 0.82, -0.14, math.cos(a) * r * 0.82), (0.08 * r, 0.04, 0.22 * r),
                      m((0.1, 0.12, 0.18), 0.5, key="tick"), self.root, bevel=0)
            tk.rotation_euler = (0, a, 0)
        self.hands = []
        for L, w in ((0.5, 0.09), (0.78, 0.06)):
            hj = joint(name + "_hand", (0, -0.2, 0), self.root)
            rbox((0, 0, L * r / 2), (w * r, 0.04, L * r), m((0.08, 0.1, 0.16), 0.4, key="hand"), hj, bevel=0)
            self.hands.append(hj)
        ball((0, -0.22, 0), 0.08 * r, m((0.85, 0.2, 0.15), 0.4, key="hub"), self.root, seg=16)

    def set(self, hours):
        """hours since 12:00 (float)."""
        self.hands[0].rotation_euler = (0, hours / 12 * 2 * math.pi, 0)
        self.hands[1].rotation_euler = (0, hours * 2 * math.pi, 0)


# ---------------------------------------------------------------- the Earth
def earth(loc=(0, 0, 0), r=10.0, night=False, name="earth"):
    """Planet: ocean + noise continents, cloud shell, thin blue atmosphere glow. night=True adds city lights."""
    root = joint(name, loc)
    mm = bpy.data.materials.new(name + "_surface")
    nt = mm.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 1.6
    nz.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.52, (*lin((0.04, 0.16, 0.42)), 1)
    e[1].position, e[1].color = 0.56, (*lin((0.25, 0.45, 0.2)), 1)
    e3 = e.new(0.68)
    e3.color = (*lin((0.55, 0.48, 0.3)), 1)
    nt.links.new(nz.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.5
    if night:
        land = nt.nodes.new("ShaderNodeMath")
        land.operation = "GREATER_THAN"
        land.inputs[1].default_value = 0.55
        nt.links.new(nz.outputs["Fac"], land.inputs[0])
        vor = nt.nodes.new("ShaderNodeTexVoronoi")
        vor.inputs["Scale"].default_value = 60.0
        nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
        dots = nt.nodes.new("ShaderNodeMath")
        dots.operation = "LESS_THAN"
        dots.inputs[1].default_value = 0.12
        nt.links.new(vor.outputs["Distance"], dots.inputs[0])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        nt.links.new(land.outputs[0], mul.inputs[0])
        nt.links.new(dots.outputs[0], mul.inputs[1])
        sc = nt.nodes.new("ShaderNodeMath")
        sc.operation = "MULTIPLY"
        sc.inputs[1].default_value = 12.0
        nt.links.new(mul.outputs[0], sc.inputs[0])
        b.inputs["Emission Color"].default_value = (*lin((1.0, 0.78, 0.4)), 1)
        nt.links.new(sc.outputs[0], b.inputs["Emission Strength"])
        self_lights = sc
    else:
        self_lights = None
    surf = ball((0, 0, 0), r, mm, root, seg=96, name=name + "_ball")
    ball((0, 0, 0), r * 1.04, glow((0.45, 0.7, 1.0), 0.6, 0.12, key="atmo"), root, seg=64, name=name + "_atmo")
    return {"root": root, "surface": surf, "lights": self_lights}


# ---------------------------------------------------------------- tamatebako
class Tamatebako:
    """Black lacquer box with a red cord; the lid hinges open; smoke puffs, clock hands and stars rise out."""

    def __init__(self, loc, s=1.0, seed=4, name="box"):
        rnd = random.Random(seed)
        self.s = s
        self.root = joint(name, loc)
        lac = m((0.05, 0.04, 0.04), 0.15, coat=1.0, key="lacquer")
        red = m((0.8, 0.12, 0.1), 0.5, key="cord")
        gold = m((0.95, 0.75, 0.3), 0.3, metal=0.8, key="gold2")
        rbox((0, 0, 0.18 * s), (0.5 * s, 0.4 * s, 0.36 * s), lac, self.root, bevel=0.03 * s)
        rbox((0, -0.201 * s, 0.18 * s), (0.3 * s, 0.005 * s, 0.2 * s), gold, self.root, bevel=0)
        self.lid = joint(name + "_lid", (0, 0.2 * s, 0.36 * s), self.root)
        rbox((0, -0.2 * s, 0.05 * s), (0.54 * s, 0.44 * s, 0.1 * s), lac, self.lid, bevel=0.03 * s)
        torus((0, -0.2 * s, 0.1 * s), 0.06 * s, 0.015 * s, red, self.lid)
        self.puffs, self.bits = [], []
        for i in range(26):
            p = ball((0, 0, 0.3 * s), 0.12 * s, glow((0.95, 0.95, 1.0), 0.7, 0.18, key="smoke"), self.root, seg=16,
                     name="puff")
            p.scale = (0.001,) * 3
            self.puffs.append((p, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.4, 1.0), rnd.uniform(0, 0.8)))
        for i in range(18):
            kind = i % 2
            if kind:
                o = rbox((0, 0, 0), (0.02 * s, 0.01 * s, 0.14 * s), glow((1.0, 0.85, 0.5), 6.0, key="hand_glow"),
                         self.root, bevel=0, name="hand_bit")
            else:
                o = ball((0, 0, 0), 0.025 * s, glow((0.8, 0.9, 1.0), 10.0, key="star_bit"), self.root, seg=8,
                         name="star_bit")
            o["base"] = tuple(o.scale) if kind else (0.025 * s,) * 3
            o.scale = (0.001,) * 3
            self.bits.append((o, rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 0.9), rnd.uniform(0, 1.0)))

    def open(self, t, t_open=0.5):
        """t seconds since the start; the lid flips at t_open, smoke rises after it."""
        s = self.s
        k = min(1.0, max(0.0, (t - t_open) / 0.5))
        self.lid.rotation_euler = (-1.9 * (1 - (1 - k) ** 3), 0, 0)
        tau = t - t_open
        for p, a, sp, d in self.puffs:
            q = tau - d
            if q <= 0:
                p.scale = (0.001,) * 3
                continue
            r = 0.25 * s * q * sp
            p.location = (math.cos(a + q) * r, math.sin(a + q) * r, (0.35 + 0.9 * q * sp) * s)
            g = 0.12 * s * min(1.0, q * 1.2) * (1 + 1.2 * q)
            p.scale = (g, g, g)
        for o, a, sp, d in self.bits:
            q = tau - d
            if q <= 0:
                o.scale = (0.001,) * 3
                continue
            r = 0.35 * s * q * sp
            o.location = (math.cos(a + 1.5 * q) * r, math.sin(a + 1.5 * q) * r, (0.4 + 0.8 * q * sp) * s)
            o.rotation_euler = (q * 3, q * 2, 0)
            o.scale = o["base"]
