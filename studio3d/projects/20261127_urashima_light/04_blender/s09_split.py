"""41.1-46.1 s: the shock wave splits the sea in two (walls of water) and a streak of light shoots into the sky."""
import random

from _common import aim, camera, ease, lerp, lerp3, math, sea, shake
from studio3d.lib.smooth import ball, rbox

SECONDS = 5.0


def build(ctx):
    w = sea.sunset_beach()
    w["sea"].hide_render = True
    wm = sea.water_mat()
    wall_m = sea.water_mat("wall_water", base=(0.18, 0.55, 0.62), rough=0.1, ripple=0.8)
    foam = sea.m((0.96, 0.97, 0.98), 0.6)
    halves = []
    for sx in (-1, 1):
        halves.append(rbox((0, 300, 0.02), (450, 600, 0.04), wm, bevel=0, name="sea_half"))
    rbox((0, 300, -9), (60, 600, 0.2), sea.m((0.45, 0.42, 0.36), 0.9), bevel=0, name="seabed")
    walls = [rbox((0, 300, 0), (5, 600, 1), wall_m, bevel=2.0, name="wall") for _ in (-1, 1)]
    caps = [rbox((0, 300, 0), (5.6, 600, 0.8), foam, bevel=0.35, name="foam_cap") for _ in (-1, 1)]
    beam = ball((0, 0, 0), 1.0, sea.glow((0.8, 0.95, 1.0), 25.0), seg=24, name="beam")
    rnd = random.Random(9)
    spray = [(ball((0, 0, -50), 0.6, sea.glow((0.9, 0.97, 1.0), 1.2, 0.6, key="spray2"), seg=10),
              rnd.choice((-1, 1)), rnd.uniform(5, 300), rnd.uniform(6, 18)) for _ in range(90)]
    return {"halves": halves, "walls": walls, "caps": caps, "beam": beam, "spray": spray, "cam": camera(24)}


def pose(ctx, h, t):
    k = ease(t / 2.2)
    gap = lerp(0.0, 34.0, k)
    hw = lerp(0.1, 14.0, ease(t / 1.6))
    for sx, half, wall, cap in zip((-1, 1), h["halves"], h["walls"], h["caps"]):
        half.location = (sx * (225 + gap / 2), 300, 0.02)
        wall.location = (sx * (gap / 2 + 2.5), 300, hw / 2 - 0.5)
        wall.scale = (1, 1, max(0.05, hw))
        cap.location = (sx * (gap / 2 + 2.5), 300, hw - 0.5)
    for b, sx, y, up in h["spray"]:
        q = t - 0.15 - y / 250.0
        b.location = (sx * (gap / 2 + 3 + 6 * max(0, q)), y, max(-5, up * q - 4.9 * q * q) + hw * 0.8) if q > 0 else (0, 0, -50)
    # the light streak: along the channel, then climbing into the sky
    q = ease((t - 0.3) / 1.6)
    L = lerp(1, 260, q)
    rise = ease((t - 2.4) / 1.6)
    h["beam"].location = (0, 8 + L / 2, 1.5 + rise * 60)
    h["beam"].scale = (0.8, L / 2, 0.8)
    h["beam"].rotation_euler = (math.radians(-28) * rise, 0, 0)
    (sx, sy, sz), roll = shake(t, 0.08 * max(0.0, 1 - t / 2.5) + 0.01)
    aim(h["cam"], lerp3((22, -46, 34), (14, -40, 40), ease(t / SECONDS)), (0, 70, 0), roll=roll)
