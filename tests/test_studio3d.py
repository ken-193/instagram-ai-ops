"""studio3d: project specs are consistent, chunks cover every frame, assembly + QC work on synthetic frames."""
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

from studio3d import assemble
from studio3d import run as runner

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = sorted((ROOT / "studio3d/projects").glob("*/04_blender/project.json"))


def test_projects_follow_the_rules():
    assert PROJECTS
    for p in PROJECTS:
        pr = json.loads(p.read_text(encoding="utf-8"))
        assert pr["name"] == p.parents[1].name
        assert re.fullmatch(r"\d{8}_[a-z0-9_]+", pr["name"])
        for sc in pr["scenes"]:
            assert 5.0 <= sc["seconds"] <= 10.0, "1シーン5〜10秒"
            src = (p.parent / sc["file"]).read_text(encoding="utf-8")
            m = re.search(r"^SECONDS = ([\d.]+)", src, re.M)
            assert m and float(m.group(1)) == sc["seconds"]
            assert "def build(ctx)" in src and "def pose(ctx, h, t)" in src
        for d in ("01_planning", "02_script", "03_storyboard"):
            assert any((p.parents[1] / d).glob("*.md")), d


def test_matrix_covers_every_frame_once():
    for p in PROJECTS:
        name = p.parents[1].name
        pr = runner.project(name)
        m = runner.matrix(name, "final")
        for sc in pr["scenes"]:
            frames = [f for c in m if c["scene"] == sc["id"] for f in range(c["start"], c["end"])]
            assert frames == list(range(int(round(sc["seconds"] * 30))))
        assert all(c["end"] - c["start"] <= 30 for c in m)


def test_assemble_and_qc_on_synthetic_frames(tmp_path, monkeypatch):
    proj = tmp_path / "projects" / "20990101_synthetic"
    (proj / "04_blender").mkdir(parents=True)
    (proj / "04_blender" / "project.json").write_text(json.dumps(
        {"name": "20990101_synthetic", "scenes": [{"id": "s01", "file": "x.py", "seconds": 1.0},
                                                   {"id": "s02", "file": "y.py", "seconds": 1.0}]}))
    for sid in ("s01", "s02"):
        d = proj / "05_render" / "frames" / sid
        d.mkdir(parents=True)
        for f in range(30):
            a = np.zeros((96, 54, 3), np.uint8)
            a[:, :, 1] = 80 + f * 4
            a[f * 3:f * 3 + 10, :, 0] = 255
            Image.fromarray(a).save(d / f"{f:04d}.png")
    monkeypatch.setattr(assemble, "HERE", tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "render.json").write_text((ROOT / "studio3d/config/render.json").read_text())
    assemble.main(["20990101_synthetic", "--no-upload"])
    qc = json.loads((proj / "07_final" / "qc.json").read_text())
    assert qc["passed"], qc
    assert (proj / "07_final" / "20990101_synthetic_contact_sheet.jpg").exists()


def test_rerun_only_renders_missing_frames():
    name = PROJECTS[0].parents[1].name
    done = ["frames-s01-0-12", "frames-s01-30", "other-artifact"]
    m = runner.matrix(name, "final", done)
    s01 = [f for c in m if c["scene"] == "s01" for f in range(c["start"], c["end"])]
    assert not set(s01) & (set(range(0, 12)) | set(range(30, 60)))
    assert set(range(12, 30)) <= set(s01)


# ---------------------------------------------------------------- soundtrack (audio3d)
def _fake_synth(seconds_per_char=0.12):
    import numpy as np

    from pipeline import audio

    def synth(text, backend, cache, **kw):
        return np.full(int(len(text) * seconds_per_char * audio.SR), 0.1, np.float32)
    return synth


def test_no_night_soundtrack_fits_and_mixes(tmp_path):
    import json

    from pipeline import audio
    from studio3d import audio3d
    d = ROOT / "studio3d/projects/20261106_no_night"
    pr = json.loads((d / "04_blender/project.json").read_text(encoding="utf-8"))
    cfg = audio3d.load(d)
    assert cfg and set(cfg["scenes"]) <= {s["id"] for s in pr["scenes"]}
    for sc in cfg["scenes"].values():
        for _at, name, _g in sc.get("sfx", []):
            assert name in audio.SFX
    stereo, rows = audio3d.build(pr, cfg, tmp_path, synth=_fake_synth())
    assert stereo.shape == (int(50 * audio.SR), 2)
    assert len(rows) == 11


def test_soundtrack_rejects_narration_that_overruns(tmp_path):
    import pytest

    from studio3d import audio3d
    pr = {"scenes": [{"id": "s01", "seconds": 5.0}, {"id": "s02", "seconds": 5.0}]}
    cfg = {"scenes": {"s01": {"narration": [{"at": 1.0, "text": "あ" * 40}]}}}
    with pytest.raises(SystemExit, match="ends at"):
        audio3d.build(pr, cfg, tmp_path, synth=_fake_synth())


def test_readback_check_report(tmp_path, monkeypatch):
    import sys
    import types

    from studio3d import audio3d
    heard = {"よるが、こなかった。": "夜が来なかった", "まぶしくて、ねむれない。": "ネコが走る"}

    class FakeModel:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setitem(sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel))
    from pipeline import narration_check as nc
    monkeypatch.setattr(nc, "transcribe", lambda m, a, sr, vad=False: heard[a.tag])

    class Clip(list):
        tag = ""
    rows = []
    for t in heard:
        c = Clip()
        c.tag = t
        rows.append({"scene": "s01", "text": t, "tts": t, "audio": c})
    ok, md = audio3d.readback_check(rows, tmp_path)
    assert not ok and "NG" in md and (tmp_path / "narration_check.md").exists()
