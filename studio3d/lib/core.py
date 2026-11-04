"""Shared Blender (bpy) building blocks for 世界の仕様外 3D scenes.

Everything here runs inside Blender's Python (`pip install bpy`). Scenes must be deterministic:
the picture at frame N depends only on N, so frame ranges can render in parallel on different machines.
"""
from __future__ import annotations

import math

import bpy
from mathutils import Euler, Vector


# ---------------------------------------------------------------- render setup
def setup(width=1080, height=1920, fps=30, samples=12):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import addon_utils
    addon_utils.enable("cycles", default_set=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = width, height
    sc.render.resolution_percentage = 100
    sc.render.fps = fps
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Punchy"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    return sc


# ---------------------------------------------------------------- materials / objects
def mat(name, base, rough=0.5, coat=0.0, sss=0.0, transmission=0.0, ior=1.45, bump=None, emit=None, alpha=1.0):
    """Principled material. bump = (scale, strength, "dimple"|"noise")."""
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


def sphere(name, loc, scale, material, seg=64, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=max(8, seg // 2), location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material)
    if parent is not None:
        o.parent = parent
    return o


def empty(name, loc=(0, 0, 0)):
    bpy.ops.object.empty_add(location=loc)
    o = bpy.context.object
    o.name = name
    return o


def nishita_sky(strength=0.32, sun_elevation=24, sun_rotation=120):
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    nt = w.node_tree
    s = nt.nodes.new("ShaderNodeTexSky")
    try:
        s.sky_type = "NISHITA"
        s.sun_elevation = math.radians(sun_elevation)
        s.sun_rotation = math.radians(sun_rotation)
    except Exception:
        pass
    nt.links.new(s.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    nt.nodes["Background"].inputs["Strength"].default_value = strength


def sun(energy=1.6, elevation=55, azimuth=140, angle=3):
    bpy.ops.object.light_add(type="SUN", rotation=(math.radians(elevation), 0, math.radians(azimuth)))
    L = bpy.context.object
    L.data.energy = energy
    L.data.angle = math.radians(angle)
    return L


def area_light(loc, rot_deg, energy, size):
    bpy.ops.object.light_add(type="AREA", location=loc)
    L = bpy.context.object
    L.data.energy, L.data.size = energy, size
    L.rotation_euler = Euler(tuple(math.radians(a) for a in rot_deg))
    return L


# ---------------------------------------------------------------- camera
def camera(lens=26, dof=None):
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    cam.data.lens = lens
    cam.data.clip_end = 2000
    if dof:
        cam.data.dof.use_dof = True
        cam.data.dof.focus_distance, cam.data.dof.aperture_fstop = dof
    return cam


def aim(cam, loc, target, roll=0.0, lens=None):
    cam.location = Vector(loc)
    e = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    e.rotate_axis("Z", roll)
    cam.rotation_euler = e
    if lens:
        cam.data.lens = lens


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, q):
    return a + (b - a) * q


def lerp3(a, b, q):
    return tuple(lerp(x, y, q) for x, y in zip(a, b))


def shake(t, amp, freq=1.0):
    """Hand-held / impact shake offset (x, y, z) and roll; amp in metres."""
    return (math.sin(t * 23.1 * freq) * amp + math.sin(t * 57.7 * freq) * amp * 0.4,
            math.sin(t * 19.3 * freq + 1.0) * amp * 0.6,
            math.sin(t * 31.9 * freq + 2.0) * amp), math.sin(t * 13.7 * freq) * amp * 0.08


def slowmo(t, start, end, rate):
    """Scene time -> action time, slowed between start and end (rate < 1 = slow motion)."""
    if t <= start:
        return t
    if t <= end:
        return start + (t - start) * rate
    return start + (end - start) * rate + (t - end)


def orbit(center, radius, angle, height):
    return (center[0] + math.cos(angle) * radius, center[1] + math.sin(angle) * radius, center[2] + height)
