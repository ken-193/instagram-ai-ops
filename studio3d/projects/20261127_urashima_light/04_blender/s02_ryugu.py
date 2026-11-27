"""6.5-12 s: Ryugu. Vermilion palace under the sea, a ring of dancing fish, lanterns; Taro arrives on the turtle."""
from _common import aim, camera, ease, lerp, math, rider, sea

SECONDS = 5.5
COLS = [(0.95, 0.35, 0.3), (0.97, 0.75, 0.4), (0.4, 0.62, 0.95), (0.95, 0.55, 0.65)]


def build(ctx):
    w = sea.ryugu()
    fish = []
    for i in range(14):
        f = sea.Fish((0, 0, 0), COLS[i % 4], 1.1 + 0.2 * (i % 3), name="fish%d" % i)
        fish.append(f)
    tu = sea.SeaTurtle((0, 0, 0), 1.2)
    tr = rider(tu)
    return {"fish": fish, "t": tu, "tr": tr, "w": w, "cam": camera(24)}


def pose(ctx, h, t):
    for i, f in enumerate(h["fish"]):                              # the 舞い踊り: a turning, bobbing ring
        a = i / len(h["fish"]) * 2 * math.pi + t * 0.9
        f.root.location = (math.cos(a) * 8.5, -12 + math.sin(a) * 4.5, 4.5 + 1.2 * math.sin(a * 2 + t * 3))
        f.root.rotation_euler = (0, 0.25 * math.sin(t * 3 + i), a)
        f.swim(t, i)
    for j, L in enumerate(h["w"]["lanterns"]):
        L.scale = (0.6 * (1 + 0.05 * math.sin(t * 7 + j)),) * 2 + (0.8,)
    k = ease(t / 3.6)
    tu = h["t"]
    tu.root.location = (lerp(-10, -3, k), lerp(-14, -18, k), lerp(10, 4.5, k))
    tu.root.rotation_euler = (0, 0, math.radians(lerp(140, 160, k)))
    tu.swim(t, 0.8)
    a = lerp(-2.05, -1.62, ease(t / SECONDS))
    aim(h["cam"], (math.cos(a) * 40, math.sin(a) * 40 + 4, lerp(7, 9, ease(t / SECONDS))), (0, -4, 6.5))
