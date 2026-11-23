"""Shared set for the maneki-neko film: one shotengai, one cat (30 m), the same everywhere."""
import math

from _common import daylight
from studio3d.lib.smooth import ManekiNeko, SoftPerson, YUKATA, far_hills, plaza, shotengai, town_blocks

CAT_Y = 82.0           # the cat stands in the plaza where the street opens out


def _skip(x, y):
    in_street = abs(x) < 11 and y < 70
    in_plaza = abs(x) < 36 and 52 < y < 112
    return in_street or in_plaza


def set_and_cat(seed=3, cat_y=CAT_Y):
    st = shotengai(length=45.0, seed=seed)
    plaza((0, CAT_Y))
    town_blocks(_skip)
    far_hills()
    sky, sun = daylight(45, 200, 0.45, 3.4)
    neko = ManekiNeko((0, cat_y, 0), s=1.0)
    return st, neko


def dancer(name, loc, yaw, i):
    onna = i % 2 == 0
    p = SoftPerson(name, loc, yaw, 1.6 if onna else 1.72, skin=i % 2, hair=0, outfit="yukata" if onna else "happi",
                   yukata=YUKATA[i % len(YUKATA)] if onna else (0.15, 0.25, 0.55),
                   accent=(0.95, 0.85, 0.3) if onna else (0.95, 0.3, 0.25), hat="amigasa" if onna else None)
    p.kind = "onna" if onna else "otoko"
    p.phase = (i * 0.37) % 1.0
    return p


def shopper(name, loc, yaw, i):
    return SoftPerson(name, loc, yaw, 1.5 + 0.25 * ((i * 7) % 3) / 2, skin=i % 3, hair=i % 3, shirt=i, pants=i % 3)


# ---------------------------------------------------------------- crowds via collection instances
def _hierarchy(root):
    return [root] + list(root.children_recursive)


def to_collection(root, name):
    import bpy
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    for o in _hierarchy(root):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    return col


def dance_templates(n=4):
    """n posed dancers kept in hidden collections; instances mirror whatever pose they have this frame."""
    import bpy
    out = []
    for k in range(n):
        p = dancer(f"tmpl{k}", (0, 0, 0), 0.0, k)
        p.phase = k * 0.27
        col = to_collection(p.root, f"tmpl{k}")
        bpy.context.view_layer.layer_collection.children[col.name].exclude = True
        out.append((p, col))
    return out


def instance(col, loc, yaw):
    import bpy
    e = bpy.data.objects.new("inst", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = col
    e.location = loc
    e.rotation_euler = (0, 0, yaw)
    bpy.context.scene.collection.objects.link(e)
    return e


def flying_bits(n, seed, colours, size=(0.25, 0.18, 0.01)):
    """Confetti / leaves: flat pieces whose path is computed in pose (deterministic)."""
    import random as _r
    from studio3d.lib.smooth import m, rbox
    rnd = _r.Random(seed)
    bits = []
    for i in range(n):
        o = rbox((0, 0, -50), size, m(rnd.choice(colours), 0.6), bevel=0)
        bits.append({"o": o, "v": (rnd.uniform(-9, 9), rnd.uniform(-14, -3), rnd.uniform(6, 16)),
                     "spin": (rnd.uniform(-9, 9), rnd.uniform(-9, 9), rnd.uniform(-9, 9)), "drag": rnd.uniform(0.5, 1.2)})
    return bits


def place_bits(bits, origin, tau):
    """Burst from origin at tau=0, float down with drag (leaves fall slowly)."""
    for b in bits:
        o = b["o"]
        if tau < 0:
            o.location = (0, 0, -50)
            continue
        k = 1 - math.exp(-b["drag"] * tau)
        x = origin[0] + b["v"][0] * k / b["drag"]
        y = origin[1] + b["v"][1] * k / b["drag"]
        z = origin[2] + b["v"][2] * k / b["drag"] - 1.2 * tau * tau * 0.5
        o.location = (x, y, max(0.02, z))
        o.rotation_euler = tuple(s * tau for s in b["spin"])
