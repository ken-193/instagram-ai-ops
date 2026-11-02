"""Tiny flat-shaded 3D renderer for blocky (voxel-style) worlds, drawn with Pillow.

  * perspective camera with roll (for shake) and near-plane clipping
  * boxes (any rotation) -> 6 quads, back-face culled, sun + ambient shading, distance fog
  * painter's algorithm (faces sorted far -> near); ground and decals drawn first
  * sprites (tiny crowd figures) and translucent billboards (dust, shock rings) share the depth sort

Units are metres; y is up. Everything is plain numpy/Pillow so it renders in the same worker processes
as the 2D scenes (pipeline.build).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw

from .engine import H, W, Canvas, clamp, mix

SUN = np.array([-0.45, 0.8, -0.4])
SUN = SUN / np.linalg.norm(SUN)
NEAR = 0.4


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


I3 = np.eye(3)

# corner index = 4*(sx>0) + 2*(sy>0) + (sz>0)
_SIGNS = np.array([[(1 if i & 4 else -1), (1 if i & 2 else -1), (1 if i & 1 else -1)] for i in range(8)], float)
_FACES = [((0, 1, 3, 2), (-1, 0, 0)), ((4, 6, 7, 5), (1, 0, 0)), ((0, 4, 5, 1), (0, -1, 0)),
          ((2, 3, 7, 6), (0, 1, 0)), ((0, 2, 6, 4), (0, 0, -1)), ((1, 5, 7, 3), (0, 0, 1))]


class Camera:
    def __init__(self, eye, target, fov=62.0, roll=0.0):
        self.eye = np.asarray(eye, float)
        fwd = np.asarray(target, float) - self.eye
        fwd /= (np.linalg.norm(fwd) or 1)
        up = np.array([0.0, 1.0, 0.0])
        right = np.cross(fwd, up)
        if np.linalg.norm(right) < 1e-6:
            right = np.array([1.0, 0, 0])
        right /= np.linalg.norm(right)
        up2 = np.cross(right, fwd)
        c, s = math.cos(roll), math.sin(roll)
        right, up2 = right * c + up2 * s, up2 * c - right * s
        self.R = np.stack([right, up2, fwd])
        self.f = (H / 2) / math.tan(math.radians(fov) / 2)

    def to_cam(self, P):
        return (np.asarray(P, float) - self.eye) @ self.R.T

    def project(self, Pc):
        Pc = np.atleast_2d(Pc)
        z = Pc[:, 2]
        return np.stack([W / 2 + self.f * Pc[:, 0] / z, H / 2 - self.f * Pc[:, 1] / z], axis=1)

    def scale_at(self, depth):
        return self.f / max(depth, 1e-3)


def clip_near(poly_c):
    """Sutherland-Hodgman against z = NEAR in camera space."""
    out = []
    n = len(poly_c)
    for i in range(n):
        a, b = poly_c[i], poly_c[(i + 1) % n]
        ina, inb = a[2] >= NEAR, b[2] >= NEAR
        if ina:
            out.append(a)
        if ina != inb:
            t = (NEAR - a[2]) / (b[2] - a[2])
            out.append(a + (b - a) * t)
    return out


@dataclass
class Box:
    c: np.ndarray          # centre (world)
    h: np.ndarray          # half sizes
    R: np.ndarray          # rotation
    color: tuple
    edge: bool = True      # draw darker outlines (characters)
    glow: bool = False     # unlit (eyes, lanterns)
    deco: str = ""         # "windows" for buildings


@dataclass
class Scene3D:
    cam: Camera
    sky: tuple = ((150, 196, 226), (238, 232, 214))
    fog: tuple = (226, 226, 220)
    fog_start: float = 120.0
    fog_end: float = 700.0
    fog_max: float = 0.75
    boxes: list = field(default_factory=list)
    decals: list = field(default_factory=list)      # flat polygons on the ground: (world pts Nx3, rgba)
    sprites: list = field(default_factory=list)     # (world pos, height m, body rgb, head rgb)
    bills: list = field(default_factory=list)       # (world pos, radius m, rgba) translucent discs
    lines: list = field(default_factory=list)       # 3D polylines over everything: (pts Nx3, rgba, width px)

    def box(self, c, size, color, R=I3, **kw):
        self.boxes.append(Box(np.asarray(c, float), np.asarray(size, float) / 2, R, tuple(color), **kw))

    # -------------------------------------------------------------- rendering
    def _shade(self, rgb, n, centre):
        lam = 0.58 + 0.42 * max(0.0, float(n @ SUN)) + (0.06 if n[1] > 0.5 else 0.0)
        col = tuple(int(clamp(c * lam / 255, 0, 1) * 255) for c in rgb)
        d = float(np.linalg.norm(centre - self.cam.eye))
        f = clamp((d - self.fog_start) / (self.fog_end - self.fog_start)) * self.fog_max
        return mix(col, self.fog, f), f

    def _poly2d(self, world_pts):
        pc = self.cam.to_cam(world_pts)
        if (pc[:, 2] < NEAR).any():
            pc = clip_near(list(pc))
            if len(pc) < 3:
                return None, None
            pc = np.array(pc)
        return self.cam.project(pc), float(pc[:, 2].mean())

    def render(self, cv: Canvas, ground=(150, 150, 140)):
        k = cv.ss
        # sky
        mask = Image.linear_gradient("L").resize((W * k, H * k))
        cv.img.paste(Image.composite(Image.new("RGBA", mask.size, self.sky[1] + (255,)),
                                     Image.new("RGBA", mask.size, self.sky[0] + (255,)), mask), (0, 0))
        d = cv.d
        # ground plane (big quad around the camera)
        e = self.cam.eye
        g = np.array([[e[0] - 2500, 0, e[2] - 2500], [e[0] + 2500, 0, e[2] - 2500],
                      [e[0] + 2500, 0, e[2] + 2500], [e[0] - 2500, 0, e[2] + 2500]])
        pts, _ = self._poly2d(g)
        if pts is not None:
            d.polygon([(x * k, y * k) for x, y in pts], fill=mix(ground, self.fog, 0.15) + (255,))
        for wp, rgba in self.decals:
            pts, depth = self._poly2d(wp)
            if pts is None:
                continue
            f = clamp((depth - self.fog_start) / (self.fog_end - self.fog_start)) * self.fog_max
            col = mix(rgba[:3], self.fog, f)
            if len(rgba) == 4 and rgba[3] < 255:
                cv.polygon([tuple(p) for p in pts], fill=col + (rgba[3],))
            else:
                d.polygon([(x * k, y * k) for x, y in pts], fill=col + (255,))
        # collect faces + sprites + billboards, sort far -> near
        items = []
        for b in self.boxes:
            corners = b.c + (_SIGNS * b.h) @ b.R.T
            for idx, nl in _FACES:
                n = b.R @ np.array(nl, float)
                fc = corners[list(idx)].mean(axis=0)
                if n @ (fc - e) >= 0:
                    continue
                pts, depth = self._poly2d(corners[list(idx)])
                if pts is None:
                    continue
                dist = float(np.linalg.norm(fc - e))
                items.append((dist, 0, (pts, b, n, fc, corners[list(idx)])))
        if self.sprites:
            P = np.array([s[0] for s in self.sprites], float)
            pc = self.cam.to_cam(P)
            vis = pc[:, 2] > NEAR + 0.5
            xy = self.cam.project(np.where(vis[:, None], pc, 1.0))
            dist = np.linalg.norm(P - e, axis=1)
            for i in np.nonzero(vis)[0]:
                x, y = xy[i]
                if -40 < x < W + 40 and -40 < y < H + 200:
                    items.append((float(dist[i]), 1, (x, y, pc[i, 2], self.sprites[i])))
        for pos, r, rgba in self.bills:
            pc = self.cam.to_cam(np.asarray(pos, float)[None])[0]
            if pc[2] <= NEAR + 0.2:
                continue
            x, y = self.cam.project(pc[None])[0]
            items.append((float(np.linalg.norm(np.asarray(pos) - e)), 2, (x, y, r * self.cam.f / pc[2], rgba)))
        items.sort(key=lambda it: -it[0])
        for dist, kind, data in items:
            if kind == 0:
                pts, b, n, fc, wpts = data
                if b.glow:
                    col, fogf = b.color, 0
                else:
                    col, fogf = self._shade(b.color, n, fc)
                poly = [(x * k, y * k) for x, y in pts]
                if b.edge:
                    d.polygon(poly, fill=col + (255,), outline=mix(col, (0, 0, 0), 0.35) + (255,),
                              width=max(1, int(1.2 * k)))
                else:
                    d.polygon(poly, fill=col + (255,))
                if b.deco == "windows" and n[1] < 0.5:
                    self._windows(cv, wpts, n, col, fogf)
            elif kind == 1:
                x, y, z, (_, hgt, body, head) = data
                s = hgt * self.cam.f / z
                if s < 1.2:
                    continue
                w = max(1.0, s * 0.3)
                d.rectangle([(x - w / 2) * k, (y - s * 0.78) * k, (x + w / 2) * k, y * k], fill=body + (255,))
                d.rectangle([(x - w * 0.6) * k, (y - s) * k, (x + w * 0.6) * k, (y - s * 0.78) * k],
                            fill=head + (255,))
            else:
                x, y, rp, rgba = data
                if rp < 0.5 or rp > 4000:
                    continue
                cv.circle(x, y, rp, fill=rgba)
        for pts3, rgba, wpx in self.lines:
            pc = self.cam.to_cam(np.asarray(pts3, float))
            if (pc[:, 2] < NEAR).any():
                continue
            xy = self.cam.project(pc)
            cv.line([tuple(p) for p in xy], fill=rgba, width=wpx)

    def _windows(self, cv: Canvas, wpts, n, col, fogf):
        """Floor bands on a vertical building face."""
        ys = wpts[:, 1]
        y0, y1 = ys.min(), ys.max()
        if y1 - y0 < 5:
            return
        lo = wpts[ys <= y0 + 1e-6]
        if len(lo) < 2:
            return
        a, b = lo[0].copy(), lo[1].copy()
        line_col = mix(mix(col, (40, 60, 80), 0.45), self.fog, fogf)
        y = y0 + 3.0
        while y < y1 - 1.5:
            a[1] = b[1] = y
            pa, _ = self._poly2d(np.array([a, b, b + [0, 1.4, 0], a + [0, 1.4, 0]]))
            if pa is not None:
                cv.d.polygon([(x * cv.ss, yy * cv.ss) for x, yy in pa], fill=line_col + (255,))
            y += 3.6


# ---------------------------------------------------------------- deterministic physics helpers
def ballistic(t, p0, v0, g=30.0, rest=0.0, bounce=0.3, friction=2.5):
    """Point thrown at t=0 from p0 with v0; bounces once on the ground (y=rest), then slides to a stop.
    Returns (pos, landed_time or None)."""
    p0, v0 = np.asarray(p0, float), np.asarray(v0, float)
    a = 0.5 * g
    disc = v0[1] ** 2 + 4 * a * (p0[1] - rest)
    tl = (v0[1] + math.sqrt(max(disc, 0))) / g
    if t <= tl:
        return p0 + v0 * t + np.array([0, -a * t * t, 0]), None
    pl = p0 + v0 * tl + np.array([0, -a * tl * tl, 0])
    pl[1] = rest
    vh = np.array([v0[0], 0, v0[2]])
    vy2 = (g * tl - v0[1]) * bounce
    tb = 2 * vy2 / g
    dt = t - tl
    if dt <= tb:
        return pl + vh * 0.6 * dt + np.array([0, vy2 * dt - a * dt * dt, 0]), tl
    p2 = pl + vh * 0.6 * tb
    ds = dt - tb
    slide = vh * 0.5 * (1 - math.exp(-friction * ds)) / friction
    return p2 + slide, tl


def debris_field(seed, n, origin, power=25.0, up=1.0, size=(1.0, 3.5)):
    rnd = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        ang = rnd.uniform(0, math.tau)
        sp = rnd.uniform(0.3, 1.0) * power
        v = np.array([math.cos(ang) * sp, rnd.uniform(0.5, 1.2) * power * up, math.sin(ang) * sp])
        s = rnd.uniform(*size)
        out.append((np.asarray(origin, float) + rnd.normal(0, 1.5, 3) * [1, 0, 1] + [0, s / 2, 0], v, s,
                    rnd.uniform(-8, 8, 3), rnd.integers(0, 4)))
    return out
