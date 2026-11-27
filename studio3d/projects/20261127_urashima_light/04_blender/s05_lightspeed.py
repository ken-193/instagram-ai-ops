"""20.8-28.1 s: the turtle (Taro aboard) swims through space; starlight stretches into lines near light speed."""
from _common import aim, camera, ease, key_lights, lerp3, math, rider, sea, shake

SECONDS = 7.6


def build(ctx):
    d = sea.deep_space()
    tu = sea.SeaTurtle((0, 0, 0), 1.0)
    tr = rider(tu)
    key_lights()
    home = [tuple(o.location) for o in d["stars"]]
    return {"t": tu, "tr": tr, "stars": d["stars"], "home": home, "cam": camera(30)}


def pose(ctx, h, t):
    tu = h["t"]
    tu.swim(t, 1.2)
    stretch = ease((t - 2.2) / 2.0)
    speed = 6 + 240 * stretch                                      # stars stream past toward +Y
    for o, (x, y, z) in zip(h["stars"], h["home"]):
        yy = (y + speed * t + 200) % 400 - 200
        o.location = (x, yy, z)
    sea.set_streaks(h["stars"], stretch)
    tu.root.location = (0, 0, 0.12 * math.sin(t * 2.0))
    (sx, sy, sz), roll = shake(t, 0.01 + 0.05 * stretch)
    k = ease(t / SECONDS)
    aim(h["cam"], lerp3((3.6, -4.6, 1.5), (2.6, -3.4, 0.9), k), (sx * 0.2, sy * 0.2, 0.7 + sz * 0.2), roll=roll)
