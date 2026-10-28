"""Automated quality checks on a rendered reel + its script. Every check is recorded;
`passed` is False if any check marked `blocking` fails."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from .render.engine import BRAND, SAFE
from .tts import CREDITS

ROOT = Path(__file__).resolve().parents[1]


def ffprobe(path: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return json.loads(r.stdout)


def _run_ff(args) -> str:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True)
    return r.stderr + ("" if r.returncode == 0 else f"\nEXIT {r.returncode}")


def run(video: Path, script: dict, timeline: dict) -> dict:
    checks: list[dict] = []

    def add(name, ok, detail, blocking=True):
        checks.append({"check": name, "ok": bool(ok), "detail": detail, "blocking": blocking})

    limits = json.loads((ROOT / "config/limits.json").read_text())
    add("file exists", video.exists() and video.stat().st_size > 100_000, f"{video.stat().st_size if video.exists() else 0} bytes")
    if not video.exists():
        return {"passed": False, "checks": checks}

    info = ffprobe(video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), {})
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    add("video codec H.264", v.get("codec_name") == "h264", v.get("codec_name"))
    add("pixel format yuv420p", v.get("pix_fmt") == "yuv420p", v.get("pix_fmt"))
    add("resolution 1080x1920 (9:16)", (v.get("width"), v.get("height")) == (1080, 1920), f"{v.get('width')}x{v.get('height')}")
    fr = v.get("r_frame_rate", "0/1").split("/")
    fps = float(fr[0]) / float(fr[1] or 1)
    add("frame rate 23-60", 23 <= fps <= 60, f"{fps:.2f} fps")
    add("audio AAC 48kHz", a.get("codec_name") == "aac" and a.get("sample_rate") == "48000",
        f"{a.get('codec_name')} {a.get('sample_rate')}Hz ch={a.get('channels')}")
    add("duration within limits", limits["min_duration_sec"] <= dur <= limits["max_duration_sec"],
        f"{dur:.2f}s (limits {limits['min_duration_sec']}-{limits['max_duration_sec']})")
    add("duration matches timeline", abs(dur - timeline["total"]) < 0.5, f"video {dur:.2f}s / timeline {timeline['total']}s")
    add("file size < 300MB (Instagram API)", size_mb < 300, f"{size_mb:.1f} MB")

    dec = _run_ff(["-v", "error", "-i", str(video), "-f", "null", "-"])
    add("full decode without errors", "EXIT" not in dec and not dec.strip(), dec.strip()[:300] or "clean")

    bd = _run_ff(["-i", str(video), "-vf", "blackdetect=d=0.5:pix_th=0.05", "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_duration:([\d.]+)", bd)
    add("no long black segments", not blacks, f"{len(blacks)} segment(s) {blacks[:5]}")

    fz = _run_ff(["-i", str(video), "-vf", "freezedetect=n=0.0005:d=2.5", "-an", "-f", "null", "-"])
    freezes = re.findall(r"freeze_duration: ([\d.]+)", fz)
    add("no frozen segments > 2.5s", not freezes, f"{len(freezes)} segment(s) {freezes[:5]}", blocking=False)

    lo = _run_ff(["-i", str(video), "-af", "ebur128=peak=true", "-vn", "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", lo)
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", lo)
    lufs = float(m[-1]) if m else None
    add("loudness about -14 LUFS", lufs is not None and -17 <= lufs <= -11, f"I={lufs} LUFS, true peak={tp[-1] if tp else '?'} dBFS")

    sub = BRAND["subtitle"]
    add("subtitle band inside safe area", SAFE["top"] < sub["center_y"] < 1920 - SAFE["bottom"] - 90,
        f"center_y={sub['center_y']}, safe y {SAFE['top']}..{1920 - SAFE['bottom']}")
    add("subtitle size readable (>=56px)", sub["font_size"] >= 56, f"{sub['font_size']}px")

    # content / compliance
    statuses = {fc["status"] for fc in script["fact_checks"]}
    cap = script["caption"]
    if statuses & {"assumption", "fiction", "estimate"}:
        add("caption discloses assumptions/fiction", any(k in cap for k in ("仮定", "思考実験", "フィクション", "概算")),
            "assumption/estimate/fiction claims present")
    unverified = [fc["claim"] for fc in script["fact_checks"] if fc["status"] == "verified" and not fc.get("source_ids")]
    add("verified claims have sources", not unverified, unverified or "ok")
    backend = script.get("tts", {}).get("backend", "openjtalk")
    if backend == "openjtalk":
        add("TTS credit (CC BY) in caption", "CC BY" in cap, CREDITS["openjtalk"])
    add("hashtags <= 15", len(script["hashtags"]) <= 15, f"{len(script['hashtags'])} tags")
    total_caption = len(cap) + 2 + len(" ".join(script["hashtags"]))
    add("caption+tags <= 2200 chars", total_caption <= 2200, f"{total_caption} chars")
    thumb = video.parent / "thumbnail.jpg"
    add("thumbnail exists", thumb.exists(), str(thumb.name), blocking=False)

    passed = all(c["ok"] for c in checks if c["blocking"])
    return {"passed": passed, "checks": checks, "duration": dur, "lufs": lufs}
