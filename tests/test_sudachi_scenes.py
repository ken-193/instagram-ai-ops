"""すだち太郎: scenes render through all shots; per-line voice overrides reach the TTS call."""
import json
from pathlib import Path

from pipeline import build, qc
from pipeline.render.engine import Canvas
from pipeline.render.scenes import SCENES, SceneCtx
from pipeline.schema import validate

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = json.loads((ROOT / "posts/IG-20261103-001/script.json").read_text(encoding="utf-8"))


def test_script_valid_and_glyphs():
    assert validate(SCRIPT, set(SCENES)) == []
    assert qc.missing_glyphs(SCRIPT) == []


def test_scenes_render():
    for sc in SCRIPT["scenes"]:
        d = sc["min_duration"]
        for f in (0.05, 0.4, 0.75, 0.97):
            cv = Canvas(1)
            SCENES[sc["type"]](cv, d * f, d, sc["params"], SceneCtx(t_global=0, lines=[(1.0, 2.5), (2.8, 4.0)]))
            img = cv.finish()
            assert img.size == (1080, 1920)
            assert img.getpixel((540, 960)) != (0, 0, 0)       # no empty frame centre


def test_line_voice_override():
    kw = build.tts_kwargs(SCRIPT, "ondoku")
    oni_line = SCRIPT["scenes"][3]["narration"][0]
    assert build.line_kwargs(kw, oni_line, "ondoku")["voice"] == "ja-JP-KeitaNeural"
    assert build.line_kwargs(kw, SCRIPT["scenes"][0]["narration"][0], "ondoku")["voice"] == kw["voice"]
