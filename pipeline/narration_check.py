"""Check that the narration is actually READ correctly (before producing / approving a reel).

  python -m pipeline.narration_check <post_id> [--out DIR] [--model small] [--tts ondoku]

For every narration line: synthesise it with the same TTS settings the build uses (cached, so the later
production re-uses the audio), transcribe it with Whisper (faster-whisper, Japanese, no prompt so the
expected text cannot bias the result), convert both the expected reading (the line's `tts`) and the
transcript to katakana with pyopenjtalk, and compare.

Outputs in DIR: narration_check.md (table), narration_check.json, narration.mp3 (all lines with short
gaps, for listening by ear). Exit code 4 if any line is below the threshold.

Limits (written into the report): speech recognition can itself guess a word from context, so a wrong
reading of a kanji (e.g. 月 read as ガツ) may come back written as the right kanji. Listening to
narration.mp3 is still the final check for single-word readings.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
THRESHOLD = 0.85

_PUNCT = re.compile(r"[\s、。，．,.！？!?…・「」『』（）()\[\]ー〜~：:；;\"'|]")
_EQUIV = str.maketrans({"ヅ": "ズ", "ヂ": "ジ", "ヲ": "オ", "ヮ": "ワ", "ヵ": "カ", "ヶ": "ケ"})


def kana(text: str) -> str:
    """Katakana reading (pyopenjtalk), normalised for comparison."""
    import pyopenjtalk

    k = pyopenjtalk.g2p(text.replace("|", ""), kana=True)
    return _PUNCT.sub("", k).translate(_EQUIV)


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def diff(a: str, b: str) -> str:
    """Human-readable differences: 期待[...] → 認識[...]"""
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op != "equal":
            out.append(f"「{a[i1:i2] or '∅'}」→「{b[j1:j2] or '∅'}」")
    return " ".join(out)


def compare(expected_tts: str, transcript: str) -> dict:
    e, r = kana(expected_tts), kana(transcript)
    s = similarity(e, r)
    return {"expected_kana": e, "heard_kana": r, "similarity": round(s, 3), "ok": s >= THRESHOLD, "exact": e == r,
            "diff": diff(e, r) if e != r else ""}


def transcribe(model, audio: np.ndarray, sr: int, vad: bool = False) -> str:
    x = audio if sr == 16000 else np.interp(np.linspace(0, len(audio) - 1, int(len(audio) * 16000 / sr)),
                                             np.arange(len(audio)), audio).astype(np.float32)
    segs, _ = model.transcribe(x, language="ja", beam_size=5, vad_filter=vad, condition_on_previous_text=False,
                               temperature=0.0)
    return "".join(s.text for s in segs).strip()


def report_md(post_id: str, rows: list[dict], backend: str, opts: dict, model_name: str) -> str:
    bad = [r for r in rows if not r["ok"]]
    L = [f"# ナレーション読み上げチェック {post_id}", "",
         f"- 音声: {backend} {opts}", f"- 聞き取り: Whisper（faster-whisper {model_name}、日本語、台本は渡さずに認識）",
         f"- 判定: 期待する読み（台本の tts）と、聞き取った文の読みをカタカナで比較。✅ 完全一致 / 🔶 差分あり"
         f"（一致率 {int(THRESHOLD * 100)}% 以上。違いの列を人が確認）/ ⚠️ {int(THRESHOLD * 100)}% 未満",
         f"- 結果: **{len(rows) - len(bad)} / {len(rows)} 行 OK**" + ("" if not bad else f"（要確認 {len(bad)} 行）"), "",
         "| # | シーン | 台本（字幕） | 期待する読み | 聞き取り結果 | 一致率 | 判定 | 違い |", "|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        L.append(f"| {i} | {r['scene']} | {r['text'].replace('|', '')} | {r['expected_kana']} | {r['transcript']} "
                 f"| {int(r['similarity'] * 100)}% | {'✅' if r['exact'] else '🔶' if r['ok'] else '⚠️'} | {r['diff'] or '-'} |")
    L += ["", "> 注意: 音声認識は文脈から単語を推測するため、漢字の読み間違い（例: 月→ガツ）が正しい漢字で"
          "書き起こされることがあります。最終確認として narration.mp3 を耳で聞いてください。", ""]
    return "\n".join(L)


def upload(post_id: str, out: Path) -> None:
    """Put the report + narration.mp3 into Drive 05_動画・音声・アニメーション素材/narration_check/<post_id>
    (never 06 / 11: this is not an approval candidate)."""
    from . import drive

    root = drive.ensure_folder("narration_check", drive.FOLDERS["05_assets"])
    folder = drive.ensure_folder(post_id, root)
    links = {}
    for name in ("narration.mp3", "narration_check.md"):
        links[name] = drive.web_link(drive.upload(out / name, folder, name))
    print(json.dumps(links, ensure_ascii=False))


def main(argv=None):
    from . import build, tts
    from .render.engine import strip_hints

    ap = argparse.ArgumentParser()
    ap.add_argument("post_id")
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default="small")
    ap.add_argument("--tts", default=None)
    ap.add_argument("--upload", action="store_true", help="only upload an existing result in --out to Drive")
    a = ap.parse_args(argv)
    if a.upload:
        upload(a.post_id, Path(a.out))
        return

    script = json.loads((ROOT / "posts" / a.post_id / "script.json").read_text(encoding="utf-8"))
    backend = a.tts or script.get("tts", {}).get("backend", "openjtalk")
    opts = build.tts_kwargs(script, backend)
    out = Path(a.out) if a.out else ROOT / "posts" / a.post_id / "out"
    out.mkdir(parents=True, exist_ok=True)

    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device="cpu", compute_type="int8")

    rows, clips = [], []
    gap = np.zeros(int(0.6 * tts.SR), np.float32)
    for sc in script["scenes"]:
        for ln in sc["narration"]:
            expected = ln.get("tts") or strip_hints(ln["text"])
            audio = tts.synth(expected, backend, ROOT / ".cache/tts", **build.line_kwargs(opts, ln, backend))
            heard = transcribe(model, audio, tts.SR)
            r = {"scene": sc["id"], "text": ln["text"], "tts": expected, "transcript": heard, **compare(expected, heard)}
            if not r["exact"]:  # Whisper sometimes fills a long pause with "……": retry with silence removed
                heard2 = transcribe(model, audio, tts.SR, vad=True)
                r2 = {**r, "transcript": heard2, **compare(expected, heard2)}
                if r2["similarity"] > r["similarity"]:
                    r = r2
            rows.append(r)
            clips += [audio, gap]
            print(f"{'OK ' if r['exact'] else 'DIF' if r['ok'] else 'NG '} {sc['id']} {int(r['similarity'] * 100):3d}%  "
                  f"台本「{strip_hints(ln['text'])}」 聞き取り「{heard}」 {r['diff']}", flush=True)

    wav = out / "narration_check.wav"
    from . import audio as audio_mod
    mono = np.concatenate(clips) if clips else np.zeros(1, np.float32)
    audio_mod.write_wav(wav, np.stack([mono, mono], axis=1))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "128k", str(out / "narration.mp3")],
                   check=True)
    wav.unlink()
    (out / "narration_check.json").write_text(json.dumps({"post_id": a.post_id, "backend": backend, "options": opts,
                                                          "model": a.model, "threshold": THRESHOLD, "lines": rows,
                                                          "tts_chars_sent": tts.ondoku_chars_used},
                                                         ensure_ascii=False, indent=2), encoding="utf-8")
    md = report_md(a.post_id, rows, backend, opts, a.model)
    (out / "narration_check.md").write_text(md, encoding="utf-8")
    print(md)
    if any(not r["ok"] for r in rows):
        sys.exit(4)


if __name__ == "__main__":
    main()
