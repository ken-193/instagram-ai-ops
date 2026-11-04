"""Pre-rendered 3D clips: missing clips fall back to 2.5D; present clips are used as the frame."""
from PIL import Image

from pipeline import clips
from pipeline.render import engine
from pipeline.render.engine import Canvas
from pipeline.render.scenes import SCENES, SceneCtx


def test_frame_lookup_and_fallback(tmp_path):
    assert clips.frame(None, "beauty", 1.0) is None
    assert clips.frame(tmp_path, "beauty", 1.0) is None
    d = tmp_path / "clips" / "beauty"
    d.mkdir(parents=True)
    for i in range(3):
        Image.new("RGB", (54, 96), (i * 100, 0, 0)).save(d / f"{i:04d}.png")
    clips._frames.cache_clear()
    assert clips.frame(tmp_path, "beauty", 0.05).getpixel((1, 1))[0] == 100   # frame 1 at 30 fps
    assert clips.frame(tmp_path, "beauty", 9.0).getpixel((1, 1))[0] == 200    # clamps to the last frame


def test_scene_uses_clip_when_available(tmp_path):
    d = tmp_path / "clips" / "beauty"
    d.mkdir(parents=True)
    Image.new("RGB", (54, 96), (255, 0, 255)).save(d / "0000.png")
    clips._frames.cache_clear()
    engine.RUNTIME["post_dir"] = tmp_path
    try:
        cv = Canvas(1)
        SCENES["sd_reveal"](cv, 0.0, 7.0, {"clip": "beauty", "telops": []}, SceneCtx(t_global=0))
        assert cv.finish().getpixel((540, 1700)) == (255, 0, 255)
    finally:
        engine.RUNTIME["post_dir"] = None
