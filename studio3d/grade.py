"""Colour grading on finished frames (before the HUD): drain saturation over time and, optionally, keep one hue.

Per-scene settings in project.json scenes[].hud.grade:
  {"sat": [[t, value], ...],          # saturation multiplier over scene time (linear in between)
   "keep": "indigo",                  # hue family that keeps its colour ("indigo" = deep 藍 blue, not the bright sky)
   "keep_w": [[t, weight], ...]}      # how strongly the kept hue survives (0..1) over time
"""
from __future__ import annotations

import numpy as np
from PIL import Image


def _interp(pts, t, default):
    if not pts:
        return default
    xs, ys = zip(*sorted(pts))
    return float(np.interp(t, xs, ys))


def indigo_mask(rgb: np.ndarray) -> np.ndarray:
    """0..1 weight for deep blue / indigo pixels (藍). Bright sky blue is excluded by its brightness."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1e-4)
    blue = np.clip((b - np.maximum(r, g) - 0.04) / 0.12, 0, 1)
    dark = np.clip((0.62 - mx) / 0.15, 0, 1)
    chroma = np.clip((sat - 0.3) / 0.2, 0, 1)
    return blue * dark * chroma


def apply(img: Image.Image, t: float, grade: dict) -> Image.Image:
    if not grade:
        return img
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    s = _interp(grade.get("sat"), t, 1.0)
    luma = (rgb @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
    out = luma + (rgb - luma) * s
    if grade.get("keep") == "indigo":
        w = _interp(grade.get("keep_w"), t, 1.0)
        m = (indigo_mask(rgb) * w)[..., None]
        out = out * (1 - m) + rgb * m
    return Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8))
