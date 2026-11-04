"""Blender (bpy) hero shots for 「もしも桃太郎がすだちから生まれたら？」 — real 3D, rounded, film-like lighting.

  python sudachi_shots.py <shot> <out_dir> [--start N --end M --res 720 --samples 16 --fps 30]

shots:
  river   : water-level tracking shot of a giant sudachi floating down a countryside river (3.4 s)
  beauty  : product-style close-up of a fresh sudachi (+ a cut half) on fresh green bokeh (8.0 s)

Runs with `pip install bpy` (Blender as a Python module, Cycles on CPU). Deterministic: every frame is a pure
function of the frame number, so frame ranges can be rendered in parallel jobs.
"""
from __future__ import annotations

import argparse
import math
import sys

import bpy
from mathutils import Euler, Vector

SHOTS = {"river": 3.4, "beauty": 8.0}


# ---------------------------------------------------------------- setup
def reset(res, samples, fps):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable("cycles", default_set=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res, int(res * 16 / 9)
    sc.render.fps = fps
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.render.image_settings.file_format = "PNG"
    return sc


def node_mat(name, base, rough=0.5, coat=0.0, sss=0.0, transmission=0.0, ior=1.45, bump=None, emit=None, alpha=1.0):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.08
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.6, 1.0, 0.3)
    if transmission:
        b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*emit[0], 1)
        b.inputs["Emission Strength"].default_value = emit[1]
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    if bump:
        scale, strength, kind = bump
        tex = nt.nodes.new("ShaderNodeTexVoronoi" if kind == "dimple" else "ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        bp = nt.nodes.new("ShaderNodeBump")
        bp.inputs["Strength"].default_value = strength
        bp.invert = kind == "dimple"
        nt.links.new(tex.outputs["Distance" if kind == "dimple" else "Fac"], bp.inputs["Height"])
        nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def obj_sphere(name, loc, scale, mat, seg=96):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat)
    return o


def sky(strength=1.0, sun_elev=35, sun_rot=40):
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    nt = w.node_tree
    bg = nt.nodes["Background"]
    s = nt.nodes.new("ShaderNodeTexSky")
    try:
        s.sky_type = "NISHITA"
        s.sun_elevation = math.radians(sun_elev)
        s.sun_rotation = math.radians(sun_rot)
    except Exception:
        pass
    nt.links.new(s.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength


def sudachi(name, loc, r, glossy=True):
    """Giant / hero sudachi: dimpled peel (voronoi bump), slight subsurface, clear coat, stem and a leaf.
    Returns the parent empty so the whole fruit can be animated."""
    bpy.ops.object.empty_add(location=loc)
    root = bpy.context.object
    root.name = name
    peel = node_mat("peel_" + name, (0.05, 0.26, 0.012), rough=0.42, coat=0.25 if glossy else 0, sss=0.05,
                    bump=(38, 0.9, "dimple"))
    body = obj_sphere(name + "_body", (0, 0, 0), (r, r, r * 0.9), peel)
    body.parent = root
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=r * 0.045, depth=r * 0.14, location=(0, 0, r * 0.92))
    stem = bpy.context.object
    stem.data.materials.append(node_mat("stem", (0.22, 0.2, 0.08), 0.7))
    stem.parent = root
    leaf_m = node_mat("leaf", (0.04, 0.2, 0.03), 0.35, coat=0.3, sss=0.2)
    leaf = obj_sphere(name + "_leaf", (r * 0.32, 0.02, r * 0.97), (r * 0.36, r * 0.12, r * 0.025), leaf_m, seg=48)
    leaf.rotation_euler = (0.1, -0.35, 0.5)
    leaf.parent = root
    return root


def camera(loc, look, lens=35, dof=None):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    cam.data.lens = lens
    direction = Vector(look) - Vector(loc)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    if dof:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance = dof[0]
        cam.data.dof.aperture_fstop = dof[1]
    return cam


def aim(cam, loc, look, roll=0.0):
    cam.location = loc
    q = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y")
    e = q.to_euler()
    e.rotate_axis("Z", roll)
    cam.rotation_euler = e


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- river
def build_river():
    sky(0.32, 24, 120)
    # water: subdivided plane with animated noise displacement + glossy dark teal
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 40, 0))
    water = bpy.context.object
    water.scale = (14, 120, 1)
    bpy.ops.object.modifier_add(type="SUBSURF")
    water.modifiers[-1].levels = water.modifiers[-1].render_levels = 5
    tex = bpy.data.textures.new("waves", "CLOUDS")
    tex.noise_scale = 0.08
    disp = water.modifiers.new("disp", "DISPLACE")
    disp.texture = tex
    disp.strength = 0.05
    disp.texture_coords = "GLOBAL"
    wm = node_mat("water", (0.01, 0.05, 0.05), rough=0.06, ior=1.33, bump=(2.0, 0.08, "noise"))
    water.data.materials.append(wm)
    # banks, grass and rocks
    grass = node_mat("grass", (0.12, 0.3, 0.06), 0.85, bump=(40, 0.3, "noise"))
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_cube_add(location=(sx * 13, 40, 0.1))
        bank = bpy.context.object
        bank.scale = (6, 120, 0.6)
        bank.rotation_euler = (0, sx * -0.12, 0)
        bpy.ops.object.modifier_add(type="BEVEL")
        bank.modifiers[-1].width, bank.modifiers[-1].segments = 0.5, 6
        bpy.ops.object.shade_smooth()
        bank.data.materials.append(grass)
    rock = node_mat("rock", (0.36, 0.34, 0.32), 0.75, bump=(8, 0.6, "noise"))
    import random
    rnd = random.Random(4)
    for i in range(26):
        sx = rnd.choice((-1, 1))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, location=(sx * rnd.uniform(6.6, 8), rnd.uniform(-4, 90), 0.1))
        o = bpy.context.object
        o.scale = (rnd.uniform(0.4, 1.1), rnd.uniform(0.4, 1.2), rnd.uniform(0.25, 0.6))
        bpy.ops.object.shade_smooth()
        o.data.materials.append(rock)
    leaves = [node_mat("tree%d" % i, c, 0.8, sss=0.1, bump=(12, 0.5, "noise"))
              for i, c in enumerate(((0.07, 0.22, 0.05), (0.1, 0.28, 0.06), (0.05, 0.18, 0.06)))]
    trunk = node_mat("trunk", (0.18, 0.12, 0.08), 0.8)
    for i in range(44):
        sx = rnd.choice((-1, 1))
        x, y = sx * rnd.uniform(11, 24), rnd.uniform(0, 110)
        h = rnd.uniform(3, 7)
        bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=h, location=(x, y, h / 2 + 0.5))
        bpy.context.object.data.materials.append(trunk)
        for k in range(3):
            obj_sphere("canopy", (x + rnd.uniform(-0.8, 0.8), y + rnd.uniform(-0.8, 0.8), h + rnd.uniform(0, 1.6)),
                       (rnd.uniform(1.4, 2.2),) * 2 + (rnd.uniform(1.2, 1.8),), rnd.choice(leaves), seg=24)
    hills = node_mat("hills", (0.18, 0.3, 0.2), 0.9)
    for i in range(7):
        obj_sphere("hill", (rnd.uniform(-90, 90), rnd.uniform(160, 240), -10), (rnd.uniform(50, 80),) * 2 + (rnd.uniform(28, 45),),
                   hills, seg=32)
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(55), 0, math.radians(140)))
    bpy.context.object.data.energy = 1.6
    bpy.context.object.data.angle = math.radians(3)
    fruit = sudachi("giant", (0, 30, 0.9), 1.8)
    cam = camera((1.2, 0, 0.35), (0, 12, 1.2), lens=22)
    return fruit, cam, water, disp


# ---------------------------------------------------------------- beauty
def build_beauty():
    w = bpy.data.worlds.new("w")
    bpy.context.scene.world = w
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.92, 0.7, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    # backdrop with soft green bokeh lights far behind
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 14, 0), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(node_mat("backdrop", (0.18, 0.42, 0.12), 0.9))
    import random
    rnd = random.Random(8)
    for i in range(30):
        col = rnd.choice(((0.75, 1.0, 0.6), (1.0, 1.0, 0.85), (0.5, 0.9, 0.5)))
        obj_sphere("bokeh", (rnd.uniform(-7, 7), rnd.uniform(8, 13), rnd.uniform(-2, 9)), (rnd.uniform(0.12, 0.6),) * 3,
                   node_mat("bk%d" % i, col, 0.5, emit=(col, rnd.uniform(0.8, 3))), seg=16)
    # wet table
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 4, -1.0))
    bpy.context.object.data.materials.append(node_mat("table", (0.55, 0.6, 0.52), 0.1, coat=0.6))
    hero = sudachi("hero", (0, 0, 0), 1.0)
    # droplets on the peel
    drop = node_mat("drop", (1, 1, 1), 0.0, transmission=1.0, ior=1.33)
    for i in range(40):
        a, b = rnd.uniform(0, math.tau), rnd.uniform(-0.6, 1.0)
        n = Vector((math.cos(a) * math.cos(b), math.sin(a) * math.cos(b), math.sin(b) * 0.9)).normalized()
        if n.y > 0.4:
            continue
        s = rnd.uniform(0.025, 0.06)
        d = obj_sphere("drop", tuple(n * 1.0 + n * s * 0.4), (s, s, s * 0.7), drop, seg=24)
        d.parent = hero
    # cut half: flesh with segments
    half = bpy.data.objects.new("half", None)
    bpy.context.collection.objects.link(half)
    half.location = (1.55, 0.8, -0.45)
    half.rotation_euler = (math.radians(70), 0, math.radians(-25))
    rind = obj_sphere("half_rind", (0, 0, 0), (0.7, 0.7, 0.25), node_mat("rind", (0.13, 0.42, 0.04), 0.4, coat=0.3, bump=(30, 0.4, "dimple")))
    rind.parent = half
    flesh_m = node_mat("flesh", (0.86, 0.9, 0.45), 0.15, sss=0.5, transmission=0.25, coat=0.6)
    fl = obj_sphere("flesh", (0, 0, 0.05), (0.62, 0.62, 0.22), flesh_m)
    fl.parent = half
    pith = node_mat("pith", (0.9, 0.92, 0.7), 0.5)
    for k in range(9):
        a = k / 9 * math.tau
        bpy.ops.mesh.primitive_cube_add(location=(math.cos(a) * 0.27, math.sin(a) * 0.27, 0.22))
        o = bpy.context.object
        o.scale = (0.25, 0.005, 0.04)
        o.rotation_euler = (0, 0, a)
        o.data.materials.append(pith)
        o.parent = half
    bpy.ops.object.light_add(type="AREA", location=(-3, -3, 4))
    key = bpy.context.object
    key.data.energy, key.data.size = 650, 4
    key.rotation_euler = Euler((math.radians(50), 0, math.radians(-40)))
    bpy.ops.object.light_add(type="AREA", location=(3, 3, 2.5))
    rim = bpy.context.object
    rim.data.energy, rim.data.size = 500, 2
    rim.rotation_euler = Euler((math.radians(-60), 0, math.radians(140)))
    cam = camera((0.6, -8, 0.9), (0.3, 0, 1.0), lens=50, dof=(8.0, 2.0))
    return hero, cam


def pose_beauty(f, fps, hero, cam):
    t = f / fps
    q = ease(t / SHOTS["beauty"])
    hero.rotation_euler = (0.08, 0, -0.4 + t * 0.06)
    a = -0.25 + 0.3 * q                                    # slow orbit + dolly in
    dist = 8.4 - 1.6 * q
    loc = (math.sin(a) * dist + 0.3, -math.cos(a) * dist, 0.8 + 0.25 * q)
    aim(cam, loc, (0.4, 0, 0.05 - 0.1 * q))
    cam.data.dof.focus_distance = (Vector(loc) - Vector((0, 0, 0))).length - 0.8


# ---------------------------------------------------------------- main
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("shot", choices=SHOTS)
    ap.add_argument("out")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--res", type=int, default=720)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--step", type=int, default=1)
    a = ap.parse_args(argv)
    sc = reset(a.res, a.samples, a.fps)
    n = int(round(SHOTS[a.shot] * a.fps))
    end = n if a.end is None else min(a.end, n)
    if a.shot == "river":
        fruit, cam, water, disp = build_river()
        poser = lambda f: pose_river_simple(f, a.fps, fruit, cam, water)
    else:
        hero, cam = build_beauty()
        poser = lambda f: pose_beauty(f, a.fps, hero, cam)
    import os
    import time
    os.makedirs(a.out, exist_ok=True)
    for f in range(a.start, end, a.step):
        poser(f)
        sc.render.filepath = os.path.join(a.out, f"{f:04d}.png")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"frame {f}/{n} {time.time() - t0:.1f}s", flush=True)


def pose_river_simple(f, fps, fruit, cam, water):
    t = f / fps
    q = t / SHOTS["river"]
    fruit.location = (math.sin(t * 0.9) * 0.3, 11 - 4.5 * ease(q), 1.15 + math.sin(t * 2.6) * 0.08)
    fruit.rotation_euler = (math.sin(t * 1.7) * 0.06, math.sin(t * 1.3) * 0.05, t * 0.25)
    water.location.y = 40 + t * 1.4                      # the wave pattern drifts with the current
    loc = (1.0 + math.sin(t * 1.9) * 0.05, 1.0 - 1.6 * ease(q), 0.28 + 0.12 * q + math.sin(t * 2.3) * 0.02)
    aim(cam, loc, (fruit.location.x * 0.5, fruit.location.y, 1.9), roll=math.sin(t * 1.1) * 0.015)


if __name__ == "__main__":
    main()
