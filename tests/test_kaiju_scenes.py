"""Voxel 3D renderer + 阿波踊り VS 巨大怪獣 scenes."""
import json
from pathlib import Path

import numpy as np

from pipeline import qc
from pipeline.render.engine import Canvas
from pipeline.render.scenes import SCENES, SceneCtx
from pipeline.render.scenes_kaiju import safe_eye
from pipeline.render.voxel3d import Camera, Scene3D, ballistic, clip_near
from pipeline.schema import validate

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = json.loads((ROOT / "posts/IG-20261102-001/script.json").read_text(encoding="utf-8"))


def test_script_valid():
    assert validate(SCRIPT, set(SCENES)) == []
    assert qc.missing_glyphs(SCRIPT) == []


def test_every_scene_renders_through_its_shots():
    for sc in SCRIPT["scenes"]:
        d = sc["min_duration"]
        for f in (0.05, 0.35, 0.65, 0.95):
            cv = Canvas(1)
            SCENES[sc["type"]](cv, d * f, d, sc["params"], SceneCtx(t_global=0, lines=[(0.4, 2.0)]))
            assert cv.finish().size == (1080, 1920)


def test_box_is_drawn_in_front_of_camera_only():
    cv = Canvas(1)
    s = Scene3D(Camera((0, 2, -20), (0, 2, 0)))
    s.box((0, 2, 0), (4, 4, 4), (200, 0, 0))
    s.render(cv)
    r, g, b = cv.finish().getpixel((540, 960))
    assert r > g + 60   # the red box covers the centre
    cv2 = Canvas(1)
    s2 = Scene3D(Camera((0, 2, 20), (0, 2, 40)))   # box behind the camera
    s2.box((0, 2, 0), (4, 4, 4), (200, 0, 0))
    s2.render(cv2)
    r, g, b = cv2.finish().getpixel((540, 960))
    assert r < g + 30   # nothing red: the box is behind the camera


def test_near_clip_and_ballistic():
    poly = [np.array([0, 0, -1.0]), np.array([1, 0, 5.0]), np.array([0, 1, 5.0])]
    assert all(p[2] >= 0.399 for p in clip_near(poly))
    p, landed = ballistic(10.0, (0, 30, 0), (0, 20, 10), g=26, rest=9)
    assert landed is not None and abs(p[1] - 9) < 1e-6


def test_camera_never_inside_a_building():
    from pipeline.render.scenes_kaiju import _bld_boxes
    b = _bld_boxes()[0]
    inside = np.array([(b[0] + b[1]) / 2, 1.0, (b[2] + b[3]) / 2])
    assert safe_eye(inside)[1] > b[4]
