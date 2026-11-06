"""Shared look for 「もしも夜がなくなったら？」: always-day sky, cameras."""
import math

import bpy

from studio3d.lib.core import aim, camera, ease, lerp, lerp3, shake


def _sky_cols(elevation):
    """Stylised diorama sky (saturated blue, warm near the horizon when the sun is low)."""
    k = min(1.0, max(0.0, elevation / 30.0))
    zen = lerp3((0.08, 0.12, 0.40), (0.02, 0.14, 0.62), k)
    hor = lerp3((1.0, 0.50, 0.25), (0.40, 0.66, 1.0), k)
    return zen, hor


def daylight(elevation=55.0, azimuth=150.0, sky_strength=0.35, sun_energy=3.2):
    """Gradient sky + sun; returns (sky, sun) so a scene can move the sun.
    (Nishita looked hazy/grey at this scale, so the world is a simple vertical gradient.)"""
    w = bpy.data.worlds.new("sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    els = ramp.color_ramp.elements
    els[0].position, els[1].position = 0.5, 0.7
    nt.nodes["Background"].inputs["Strength"].default_value = 1.0
    vs = bpy.context.scene.view_settings
    vs.look = "AgX - Punchy"
    vs.exposure = 0.45
    bpy.ops.object.light_add(type="SUN")
    sun = bpy.context.object
    sun.data.energy = 4.0 * sun_energy / 3.2
    sun.data.angle = math.radians(3.0)
    set_sun(ramp, sun, elevation, azimuth)
    return ramp, sun


def set_sun(sky, sun, elevation, azimuth=150.0):
    zen, hor = _sky_cols(elevation)
    els = sky.color_ramp.elements
    els[0].color = hor + (1.0,)
    els[1].color = zen + (1.0,)
    sun.rotation_euler = (math.radians(90 - elevation), 0, math.radians(azimuth + 90))
    sun.data.color = (1.0, lerp(0.55, 0.97, min(1, max(0, elevation / 25))), lerp(0.3, 0.92, min(1, max(0, elevation / 25))))


__all__ = ["daylight", "set_sun", "aim", "camera", "ease", "lerp", "lerp3", "shake"]
