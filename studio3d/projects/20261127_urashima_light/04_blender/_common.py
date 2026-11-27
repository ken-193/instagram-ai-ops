"""Shared helpers for 「もしも浦島太郎の話を、現実でやったら？」."""
import math

import bpy

from studio3d.lib.core import aim, camera, ease, lerp, lerp3, shake
from studio3d.lib import sea


def rider(turtle, name="taro"):
    """Taro sitting astride the turtle's shell, hands forward on the shell rim."""
    tr = sea.Taro(name)
    tr.root.parent = turtle.body
    tr.root.location = (0, 0.15, 0.33)
    tr.sit()
    for a in tr.arms:
        a.rotation_euler = (-0.9, 0, 0)
    return tr


def world_pos(obj):
    bpy.context.view_layer.update()
    return tuple(obj.matrix_world.translation)


def key_lights(target=(0, 0, 0.7), power=1.0):
    """Two soft area lights for characters in dark sets (space, blueprint)."""
    from studio3d.lib.core import area_light
    x, y, z = target
    area_light((x + 3, y - 3, z + 3.5), (50, 0, 40), 600 * power, 4)
    area_light((x - 4, y + 2, z + 0.5), (70, 0, -120), 300 * power, 4)


__all__ = ["rider", "world_pos", "key_lights", "aim", "camera", "ease", "lerp", "lerp3", "shake", "sea", "math"]
