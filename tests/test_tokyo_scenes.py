"""Smoke tests for the Tokyo/Awa-odori scenes, the festival band and the extra deliverables."""
import json
from pathlib import Path

import numpy as np

from pipeline import audio, build, qc
from pipeline.render.engine import Canvas
from pipeline.render.scenes import SCENES, SceneCtx
from pipeline.schema import validate

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = json.loads((ROOT / "posts/IG-20261101-003/script.json").read_text(encoding="utf-8"))


def test_script_valid_and_glyphs_present():
    assert validate(SCRIPT, set(SCENES)) == []
    assert qc.missing_glyphs(SCRIPT) == []


def test_every_scene_renders_at_start_middle_end():
    for sc in SCRIPT["scenes"]:
        for t in (0.0, 1.7, 4.5):
            cv = Canvas(1)
            SCENES[sc["type"]](cv, t, 4.6, sc["params"], SceneCtx(t_global=t, lines=[(0.2, 1.4), (1.6, 3.8)]))
            assert cv.finish().size == (1080, 1920)


def test_title_is_on_screen_from_the_first_frame():
    sc = SCRIPT["scenes"][0]
    blank, titled = Canvas(1), Canvas(1)
    SCENES[sc["type"]](blank, 0.0, 3.6, {**sc["params"], "title": []}, SceneCtx(t_global=0))
    SCENES[sc["type"]](titled, 0.0, 3.6, sc["params"], SceneCtx(t_global=0))
    a = np.asarray(blank.finish(), dtype=np.int16)[640:900]
    b = np.asarray(titled.finish(), dtype=np.int16)[640:900]
    assert np.abs(a - b).mean() > 5   # title band differs at t=0


def test_matsuri_band_and_stems():
    voice = [(0.5, np.ones(4800, np.float32) * 0.1)]
    out, stems = audio.mix(6.0, voice, [], bpm=128, matsuri_from=0.5, matsuri_full=3.0, stems=True)
    assert out.shape == stems["voice"].shape == stems["music_sfx"].shape
    assert np.allclose(out, stems["voice"] + stems["music_sfx"], atol=1e-5)
    assert np.abs(stems["music_sfx"][int(4 * audio.SR):]).max() > 0.05


def test_srt_format():
    tl = {"scenes": [{"start": 1.0, "lines": [{"text": "東京に、|謎の大群", "start": 0.2, "end": 1.5}]}]}
    assert build.srt(tl) == "1\n00:00:01,200 --> 00:00:02,620\n東京に、\n謎の大群\n"
