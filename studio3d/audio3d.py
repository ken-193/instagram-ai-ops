"""Soundtrack for a studio3d project: narration (TTS), sound effects and BGM, all placed on the reel's timeline.

Settings live in `04_blender/audio.json` (kept out of project.json so editing the sound does not re-render):

  {"tts": {"backend": "ondoku", "voice": "...", "speed": 1.1},
   "bgm": {"bpm": 96, "climax": 38, "gain": 0.3, "duck": 0.5, "matsuri_from": 39, "matsuri_full": 41},
   "scenes": {"s01": {"narration": [{"at": 3.0, "text": "夜が、来なかった。", "tts": "よるが、こなかった。"}],
                      "sfx": [[0.0, "tick", 1.0]]}}}

`at` is seconds from the start of the scene. Every narration line must end inside its scene and must not
overlap the next line; `build()` raises if not, so a reel never goes out with clipped speech.
Music and effects are synthesised by code (pipeline/audio.py): no third-party audio.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TAIL = 0.15            # a line may run this far past its scene end (into the cut) at most


def load(pdir: Path) -> dict | None:
    f = pdir / "04_blender" / "audio.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def tts_options(cfg: dict) -> tuple[str, dict]:
    t = cfg.get("tts", {})
    backend = t.get("backend", "ondoku")
    if backend == "ondoku":
        return backend, {"voice": t.get("voice", "ja-JP-MasaruMultilingualNeural"), "speed": t.get("speed", 1.1),
                         "pitch": t.get("pitch", 0.0)}
    if backend == "openjtalk":
        return backend, {"speed": t.get("speed", 1.1)}
    return backend, {}


def lines(pr: dict, cfg: dict) -> list[dict]:
    """Narration lines with absolute start times, in order."""
    out, t0 = [], 0.0
    for sc in pr["scenes"]:
        for ln in cfg.get("scenes", {}).get(sc["id"], {}).get("narration", []):
            out.append({"scene": sc["id"], "start": t0 + ln["at"], "scene_end": t0 + sc["seconds"],
                        "text": ln["text"], "tts": ln.get("tts") or ln["text"]})
        t0 += sc["seconds"]
    return out


def sfx_events(pr: dict, cfg: dict) -> list[tuple[float, str, float]]:
    out, t0 = [], 0.0
    for sc in pr["scenes"]:
        for at, name, gain in cfg.get("scenes", {}).get(sc["id"], {}).get("sfx", []):
            out.append((t0 + at, name, gain))
        t0 += sc["seconds"]
    return out


def build(pr: dict, cfg: dict, cache: Path, synth=None) -> tuple[np.ndarray, list[dict]]:
    """Returns (stereo float32 at pipeline.audio.SR, narration rows with their audio)."""
    from pipeline import audio, tts
    synth = synth or tts.synth
    backend, kw = tts_options(cfg)
    total = sum(s["seconds"] for s in pr["scenes"])
    rows = lines(pr, cfg)
    for r in rows:
        r["audio"] = synth(r["tts"], backend, cache, **kw)
        r["end"] = r["start"] + len(r["audio"]) / audio.SR
    problems = [f"{r['scene']}「{r['text']}」 ends at {r['end']:.2f}s, scene ends at {r['scene_end']:.2f}s"
                for r in rows if r["end"] > r["scene_end"] + TAIL]
    problems += [f"{a['scene']}「{a['text']}」 overlaps {b['scene']}「{b['text']}」"
                 for a, b in zip(rows, rows[1:]) if a["end"] > b["start"]]
    if problems:
        raise SystemExit("narration does not fit the picture:\n" + "\n".join(problems))
    b = cfg.get("bgm", {})
    stereo = audio.mix(total, [(r["start"], r["audio"]) for r in rows], sfx_events(pr, cfg), bpm=b.get("bpm", 96),
                       climax=b.get("climax"), bgm_gain=b.get("gain", 0.3), duck=b.get("duck", 0.5),
                       matsuri_from=b.get("matsuri_from"), matsuri_full=b.get("matsuri_full"))
    return stereo, rows


def readback_check(rows: list[dict], out_dir: Path, model_name: str = "medium") -> tuple[bool, str]:
    """Same check as the 2D reels (pipeline.narration_check): Whisper hears each line, compared as kana."""
    from faster_whisper import WhisperModel

    from pipeline import narration_check as nc
    from pipeline import tts
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    res = []
    for r in rows:
        heard = nc.transcribe(model, r["audio"], tts.SR)
        c = {"scene": r["scene"], "text": r["text"], "tts": r["tts"], "transcript": heard, **nc.compare(r["tts"], heard)}
        if not c["exact"]:
            heard2 = nc.transcribe(model, r["audio"], tts.SR, vad=True)
            c2 = {**c, "transcript": heard2, **nc.compare(r["tts"], heard2)}
            if c2["similarity"] > c["similarity"]:
                c = c2
        res.append(c)
    ok = all(c["ok"] for c in res)
    md = ["# ナレーション読み上げチェック", "",
          f"音声認識: faster-whisper {model_name}／基準: 1行でも一致率 {int(nc.THRESHOLD * 100)}% 未満なら保存しない", "",
          "| シーン | 台本 | 読み（tts） | 聞き取り | 一致率 | 判定 |", "|---|---|---|---|---|---|"]
    md += [f"| {c['scene']} | {c['text']} | {c['tts']} | {c['transcript']} | {int(c['similarity'] * 100)}% | "
           f"{'OK' if c['exact'] else '近い' if c['ok'] else 'NG'} |" for c in res]
    md += ["", f"結果: {'合格' if ok else '不合格'}（{sum(c['ok'] for c in res)}/{len(res)} 行）", "",
           "注意: 音声認識は文脈から漢字を補うことがあるため、1語単位の読み間違いは完成動画を聞いて最終確認してください。"]
    text = "\n".join(md) + "\n"
    (out_dir / "narration_check.md").write_text(text, encoding="utf-8")
    (out_dir / "narration_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    return ok, text


def mux(video: Path, wav: Path, out: Path):
    """Add the soundtrack (AAC, loudness-normalised for phones) without re-encoding the picture."""
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(wav), "-map", "0:v:0",
                        "-map", "1:a:0", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-800:])
