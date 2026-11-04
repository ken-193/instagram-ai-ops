"""Reusable 3D worlds and props. Same builder = same look in every scene of a project (世界観の統一)."""
from __future__ import annotations

import math
import random

import bpy

from .core import empty, mat, nishita_sky, sphere, sun


def giant_fruit(name="fruit", loc=(0, 0, 0), r=3.5):
    """Giant green citrus (sudachi-like): dimpled glossy peel, stem, leaf. Returns the root empty."""
    root = empty(name, loc)
    peel = mat(name + "_peel", (0.05, 0.26, 0.012), rough=0.42, coat=0.25, sss=0.05, bump=(38, 0.9, "dimple"))
    sphere(name + "_body", (0, 0, 0), (r, r, r * 0.9), peel, seg=96, parent=root)
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r * 0.045, depth=r * 0.14, location=(0, 0, r * 0.92))
    stem = bpy.context.object
    stem.data.materials.append(mat(name + "_stem", (0.22, 0.2, 0.08), 0.7))
    stem.parent = root
    leaf = sphere(name + "_leaf", (r * 0.32, 0.02, r * 0.97), (r * 0.36, r * 0.12, r * 0.025),
                  mat(name + "_leafm", (0.04, 0.2, 0.03), 0.35, coat=0.3, sss=0.2), seg=48, parent=root)
    leaf.rotation_euler = (0.1, -0.35, 0.5)
    return root


def japanese_river(seed=4, length=220):
    """Countryside river along +Y: rippled glossy water, grassy banks, rocks, trees, a few farmhouses,
    a small footbridge and distant hills. Returns dict(water=...)."""
    rnd = random.Random(seed)
    nishita_sky(0.32, 24, 120)
    sun(1.6, 55, 140)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, length / 2 - 20, 0))
    water = bpy.context.object
    water.name = "water"
    water.scale = (18, length, 1)
    sub = water.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 5
    tex = bpy.data.textures.new("waves", "CLOUDS")
    tex.noise_scale = 0.09
    disp = water.modifiers.new("disp", "DISPLACE")
    disp.texture, disp.strength, disp.texture_coords = tex, 0.05, "GLOBAL"
    water.data.materials.append(mat("water", (0.01, 0.05, 0.05), rough=0.06, ior=1.33, bump=(2.0, 0.08, "noise")))
    grass = mat("grass", (0.12, 0.3, 0.06), 0.85, bump=(40, 0.3, "noise"))
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(location=(sx * 15, length / 2 - 20, 0.1))
        bank = bpy.context.object
        bank.scale = (7, length, 0.6)
        bank.rotation_euler = (0, sx * -0.1, 0)
        bev = bank.modifiers.new("bev", "BEVEL")
        bev.width, bev.segments = 0.5, 6
        bpy.ops.object.shade_smooth()
        bank.data.materials.append(grass)
    rock = mat("rock", (0.36, 0.34, 0.32), 0.75, bump=(8, 0.6, "noise"))
    for _ in range(40):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, location=(rnd.choice((-1, 1)) * rnd.uniform(7.4, 9.2),
                                                                        rnd.uniform(-10, 150), 0.1))
        o = bpy.context.object
        o.scale = (rnd.uniform(0.4, 1.2), rnd.uniform(0.4, 1.3), rnd.uniform(0.25, 0.6))
        bpy.ops.object.shade_smooth()
        o.data.materials.append(rock)
    leaves = [mat("tree%d" % i, c, 0.8, sss=0.1, bump=(12, 0.5, "noise"))
              for i, c in enumerate(((0.07, 0.22, 0.05), (0.1, 0.28, 0.06), (0.05, 0.18, 0.06)))]
    trunk = mat("trunk", (0.18, 0.12, 0.08), 0.8)
    for _ in range(70):
        x, y = rnd.choice((-1, 1)) * rnd.uniform(12, 30), rnd.uniform(-10, 180)
        h = rnd.uniform(3, 8)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=h, location=(x, y, h / 2 + 0.5))
        bpy.context.object.data.materials.append(trunk)
        for _k in range(3):
            sphere("canopy", (x + rnd.uniform(-0.8, 0.8), y + rnd.uniform(-0.8, 0.8), h + rnd.uniform(0, 1.6)),
                   (rnd.uniform(1.4, 2.3),) * 2 + (rnd.uniform(1.2, 1.8),), rnd.choice(leaves), seg=24)
    wall, roof = mat("wall", (0.75, 0.68, 0.55), 0.8), mat("roof", (0.08, 0.08, 0.1), 0.5)
    for i in range(6):                                            # farmhouses for scale
        sx = rnd.choice((-1, 1))
        x, y = sx * rnd.uniform(18, 26), rnd.uniform(20, 140)
        bpy.ops.mesh.primitive_cube_add(location=(x, y, 2.0))
        h = bpy.context.object
        h.scale = (3, 4, 1.5)
        h.data.materials.append(wall)
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=4.6, depth=2.2, location=(x, y, 4.6), rotation=(0, 0, math.pi / 4))
        r = bpy.context.object
        r.scale = (0.9, 1.15, 1)
        r.data.materials.append(roof)
    wood = mat("wood", (0.35, 0.22, 0.12), 0.7)
    bpy.ops.mesh.primitive_cube_add(location=(0, 95, 3.2))         # footbridge
    br = bpy.context.object
    br.scale = (17, 1.2, 0.18)
    br.data.materials.append(wood)
    for sx in (-6, 6):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=3.4, location=(sx, 95, 1.6))
        bpy.context.object.data.materials.append(wood)
    hills = mat("hills", (0.22, 0.34, 0.3), 0.95)
    for _ in range(9):
        sphere("hill", (rnd.uniform(-160, 160), rnd.uniform(380, 480), -28),
               (rnd.uniform(60, 95),) * 2 + (rnd.uniform(34, 52),), hills, seg=32)
    return {"water": water}


def drift_water(world, t, speed=1.4):
    """The ripple pattern flows with the current."""
    world["water"].location.y = 90 + t * speed
