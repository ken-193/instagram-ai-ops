"""Build a reel from posts/<post_id>/script.json.

  python -m pipeline.build IG-20261028-001 [--preview] [--tts openjtalk|google]

Outputs (posts/<id>/out/): reel.mp4 thumbnail.jpg audio.wav timeline.json
plus posts/<id>/{script.md, caption.txt, sources.md, metadata.json, quality_check.md}
"""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing as mp
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import audio, qc, tts
from .docs import write_post_docs
from .render.engine import (FPS, H, W, Canvas, clamp, draw_background, draw_branding, draw_subtitle, ease_out,
                            strip_hints)
from .render.scenes import SCENES, SceneCtx
from .schema import validate

ROOT = Path(__file__).resolve().parents[1]
LEAD, GAP, TAIL, XFADE = 0.2, 0.12, 0.3, 0.22


# ---------------------------------------------------------------- timeline
def tts_kwargs(script: dict, backend: str, voice: str | None = None, style: str | None = None,
               speed: float | None = None) -> dict:
    cfg = script.get("tts", {})
    if backend == "openjtalk":
        return {"speed": cfg.get("speed", 1.12)}
    if backend == "gemini":
        return {"voice": voice or cfg.get("voice", "Charon"), "style": style if style is not None else cfg.get("style", "")}
    if backend == "ondoku":
        return {"voice": voice or cfg.get("voice", "ja-JP-MasaruMultilingualNeural"),
                "speed": speed if speed is not None else cfg.get("speed", 1.1), "pitch": cfg.get("pitch", 0.0)}
    return {}


def build_timeline(script: dict, backend: str, cache: Path, kw: dict | None = None) -> tuple[dict, list]:
    kw = tts_kwargs(script, backend) if kw is None else kw
    scenes, voice_events, t = [], [], 0.0
    for sc in script["scenes"]:
        cur = sc.get("lead", LEAD)  # a scene may hold its first line back (e.g. let the picture play first)
        lines = []
        for ln in sc["narration"]:
            x = tts.synth(ln.get("tts") or strip_hints(ln["text"]), backend, cache, **kw)
            d = len(x) / tts.SR
            lines.append({"text": ln["text"], "start": round(cur, 3), "end": round(cur + d, 3)})
            voice_events.append((t + cur, x))
            cur += d + GAP
        dur = max(sc.get("min_duration", 2.0), cur - GAP + TAIL)
        scenes.append({"id": sc["id"], "type": sc["type"], "start": round(t, 3), "end": round(t + dur, 3),
                       "duration": round(dur, 3), "lines": lines})
        t += dur
    return {"total": round(t, 3), "fps": FPS, "scenes": scenes}, voice_events


# ---------------------------------------------------------------- frame rendering
_G: dict = {}


def _init_worker(script, timeline, ss):
    _G.update(script=script, timeline=timeline, ss=ss)


def _scene_at(t: float) -> int:
    for i, s in enumerate(_G["timeline"]["scenes"]):
        if t < s["end"]:
            return i
    return len(_G["timeline"]["scenes"]) - 1


def _draw_scene(cv: Canvas, i: int, t_local: float, t_global: float):
    sc_meta = _G["timeline"]["scenes"][i]
    sc = _G["script"]["scenes"][i]
    ctx = SceneCtx(t_global=t_global, lines=[(l["start"], l["end"]) for l in sc_meta["lines"]])
    SCENES[sc["type"]](cv, t_local, sc_meta["duration"], sc.get("params", {}), ctx)


def render_frame(fi: int, with_subs: bool = True) -> bytes:
    t = fi / FPS
    i = _scene_at(t)
    meta = _G["timeline"]["scenes"][i]
    tl = t - meta["start"]
    cv = Canvas(_G["ss"])
    draw_background(cv, t)
    _draw_scene(cv, i, tl, t)
    if i > 0 and tl < XFADE:  # crossfade from the previous scene's last frame
        prev = Canvas(_G["ss"])
        draw_background(prev, t)
        pm = _G["timeline"]["scenes"][i - 1]
        _draw_scene(prev, i - 1, pm["duration"], t)
        a = ease_out(tl / XFADE)
        from PIL import Image
        cv.img = Image.blend(prev.img, cv.img, a)
        from PIL import ImageDraw
        cv.d = ImageDraw.Draw(cv.img)
    draw_branding(cv, t)
    if with_subs:
        sc = _G["script"]["scenes"][i]
        for ln in meta["lines"]:
            if ln["start"] - 0.05 <= tl < ln["end"] + GAP + 0.05:
                p_in = clamp((tl - ln["start"] + 0.05) / 0.2)
                draw_subtitle(cv, ln["text"], sc.get("emphasis", []), p_in)
                break
    return cv.finish().tobytes()


def render_video(script, timeline, wav: Path, out: Path, ss: int, workers: int, crf: int):
    n = int(timeline["total"] * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r",
           str(FPS), "-i", "-", "-i", str(wav),
           "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-flags", "+cgop", "-g", str(FPS * 2), "-r", str(FPS),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with mp.get_context("fork").Pool(workers, initializer=_init_worker, initargs=(script, timeline, ss)) as pool:
        for k, frame in enumerate(pool.imap(render_frame, range(n), chunksize=4)):
            proc.stdin.write(frame)
            if k % (FPS * 5) == 0:
                print(f"  frame {k}/{n}  {time.time() - t0:.0f}s", flush=True)
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")


def render_thumbnail(script, timeline, out: Path, ss: int):
    """Cover = the hook scene's final state (headline fully shown), no subtitles."""
    from PIL import Image
    _init_worker(script, timeline, ss)
    s0 = timeline["scenes"][0]
    fi = int((s0["end"] - 0.05) * FPS)
    img = Image.frombytes("RGB", (W, H), render_frame(fi, with_subs=False))
    img.save(out, quality=92)


def sfx_events(script, timeline):
    ev = []
    for sc, meta in zip(script["scenes"], timeline["scenes"]):
        for name in sc.get("sfx", []):
            if "@" in name:  # "impact@6.6" = at 6.6 s into the scene
                nm, at = name.split("@", 1)
                ev.append((meta["start"] + float(at), nm, 0.9 if nm in ("impact", "rumble", "boom") else 0.7))
            elif name == "riser":
                ev.append((max(0.0, meta["end"] - 2.0), name, 0.7))
            elif name in ("impact", "ding"):
                at = meta["start"] + (meta["lines"][1]["start"] if len(meta["lines"]) > 1 else 0.3)
                ev.append((at, name, 0.9))
            elif name == "tick":
                ev.extend((meta["start"] + meta["lines"][1]["start"] + k * 0.12, "tick", 0.5) for k in range(12)
                          if len(meta["lines"]) > 1)
            else:
                ev.append((meta["start"], name, 0.6))
    return ev


def _srt_time(x: float) -> str:
    ms = int(round(x * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def srt(timeline: dict) -> str:
    """Subtitle file (same text/timing as the burned-in subtitles; '|' hints become line breaks)."""
    out, n = [], 0
    for sc in timeline["scenes"]:
        for ln in sc["lines"]:
            n += 1
            out.append(f"{n}\n{_srt_time(sc['start'] + ln['start'])} --> {_srt_time(sc['start'] + ln['end'] + GAP)}\n"
                       + ln["text"].replace("|", "\n") + "\n")
    return "\n".join(out)


def export_scene_clips(timeline: dict, reel: Path, dest: Path):
    """Per-scene MP4s cut from the finished reel (re-encoded so every cut is frame-accurate)."""
    dest.mkdir(exist_ok=True)
    for i, sc in enumerate(timeline["scenes"], 1):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{sc['start']:.3f}", "-i", str(reel),
                        "-t", f"{sc['duration']:.3f}", "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                        str(dest / f"{i:02d}_{sc['id']}_{sc['type']}.mp4")], check=True)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("post_id")
    ap.add_argument("--preview", action="store_true", help="1x supersampling, faster")
    ap.add_argument("--tts", default=None)
    ap.add_argument("--voice", default=None, help="Gemini prebuilt voice name (e.g. Charon)")
    ap.add_argument("--style", default=None, help="Gemini speaking-style instruction")
    ap.add_argument("--speed", type=float, default=None, help="音読さん reading speed (0.3-4)")
    ap.add_argument("--out", default=None, help="output dir (default posts/<id>/out)")
    ap.add_argument("--sample", action="store_true", help="voice sample: don't touch metadata/docs of the post")
    ap.add_argument("--workers", type=int, default=max(1, mp.cpu_count()))
    a = ap.parse_args(argv)

    post_dir = ROOT / "posts" / a.post_id
    script = json.loads((post_dir / "script.json").read_text(encoding="utf-8"))
    errs = validate(script, set(SCENES))
    if errs:
        print("\n".join("SCRIPT ERROR: " + e for e in errs))
        sys.exit(2)
    limits = json.loads((ROOT / "config/limits.json").read_text())
    backend = a.tts or script.get("tts", {}).get("backend", "openjtalk")
    out = Path(a.out) if a.out else post_dir / "out"
    out.mkdir(parents=True, exist_ok=True)
    kw = tts_kwargs(script, backend, a.voice, a.style, a.speed)
    t0 = time.time()

    print("[1/5] narration + timeline")
    timeline, voice = build_timeline(script, backend, ROOT / ".cache/tts", kw)
    if not (limits["min_duration_sec"] <= timeline["total"] <= limits["max_duration_sec"]):
        print(f"WARNING: duration {timeline['total']}s outside limits")
    (out / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[2/5] audio mix")
    climax_id = script.get("bgm", {}).get("climax_scene")
    climax = next((s["start"] for s in timeline["scenes"] if s["id"] == climax_id), None)
    bg = script.get("bgm", {})

    def scene_start(sid):
        return next((s["start"] for s in timeline["scenes"] if s["id"] == sid), None) if sid else None
    mixdown, stems = audio.mix(timeline["total"], voice, sfx_events(script, timeline), bpm=bg.get("bpm", 112),
                               climax=climax, matsuri_from=scene_start(bg.get("matsuri_from_scene")),
                               matsuri_full=scene_start(bg.get("matsuri_full_scene")), stems=True,
                               music_env=[(scene_start(e["scene"]) + e["t"], e["gain"]) for e in bg.get("envelope", [])
                                          if scene_start(e["scene"]) is not None] or None)
    audio.write_wav(out / "audio.wav", mixdown)
    audio.write_wav(out / "narration.wav", stems["voice"])
    audio.write_wav(out / "bgm_sfx.wav", stems["music_sfx"])
    (out / "subtitles.srt").write_text(srt(timeline), encoding="utf-8")

    ss = 1 if a.preview else 2
    print(f"[3/5] render video ({int(timeline['total'] * FPS)} frames, ss={ss}, workers={a.workers})")
    render_video(script, timeline, out / "audio.wav", out / "reel.mp4", ss, a.workers, crf=20)
    render_thumbnail(script, timeline, out / "thumbnail.jpg", ss)
    if script.get("export_scene_clips"):
        export_scene_clips(timeline, out / "reel.mp4", out / "scenes")

    print("[4/5] quality check")
    report = qc.run(out / "reel.mp4", script, timeline, backend)

    narration_sec = sum(l["end"] - l["start"] for s in timeline["scenes"] for l in s["lines"])
    cost = 0.0 if backend in ("openjtalk", "ondoku") else None  # 音読さん: within the plan's character quota
    if backend == "gemini":  # estimate: ~25 audio tokens/s at the configured output price
        price = limits.get("gemini_tts_usd_per_million_audio_tokens", 20.0)
        cost = round(narration_sec * 25 * price / 1e6, 4)
    if a.sample:
        sample = {"post_id": a.post_id, "backend": backend, **kw, "model": tts.gemini_model_used(),
                  "duration_sec": timeline["total"], "narration_sec": round(narration_sec, 1),
                  "est_cost_usd": cost, "tts_chars": tts.ondoku_chars_used or None, "qc_passed": report["passed"], "reel_sha256": sha256(out / "reel.mp4")}
        (out / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(sample, ensure_ascii=False))
        return

    print("[5/5] docs + metadata")
    meta = {
        "post_id": a.post_id,
        "title": script["title"],
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_sec": timeline["total"],
        "tts_backend": backend,
        "tts_options": kw,
        "tts_chars_sent": tts.ondoku_chars_used or None,
        "tts_model": tts.gemini_model_used() if backend == "gemini" else None,
        "tts_credit": tts.CREDITS.get(backend),
        "render": {"engine": "pipeline.render (Pillow+ffmpeg)", "supersampling": ss, "fps": FPS, "size": f"{W}x{H}"},
        "reel_sha256": sha256(out / "reel.mp4"),
        "reel_bytes": (out / "reel.mp4").stat().st_size,
        "qc_passed": report["passed"],
        "build_seconds": round(time.time() - t0, 1),
        "cost_usd": cost,
        "categories": script["categories"],
        "tokushima_ending_type": script["tokushima_ending"]["type"],
        "hook": script["hook"],
        "preview_quality": bool(a.preview),
    }
    (post_dir / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    write_post_docs(post_dir, script, timeline, report)
    print(json.dumps({k: meta[k] for k in ("duration_sec", "reel_bytes", "qc_passed", "build_seconds")}))
    if not report["passed"]:
        sys.exit(3)


if __name__ == "__main__":
    main()
