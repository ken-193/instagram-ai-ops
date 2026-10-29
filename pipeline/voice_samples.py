"""Narration voice comparison: same reel rendered once per Gemini voice.

  python -m pipeline.voice_samples style  <voice>                 # print the style instruction for a voice
  python -m pipeline.voice_samples upload <post_id> <voice> <dir> # put <dir>/reel.mp4 into Drive 05/voice_samples
  python -m pipeline.voice_samples report <post_id> <samples_root> # one GitHub issue comparing all samples

Samples are NOT approval candidates: they go to 05_動画・音声・アニメーション素材, never to 06 or 11.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VOICES = json.loads((ROOT / "config/voices.json").read_text(encoding="utf-8"))["candidates"]


def style(voice: str) -> str:
    return VOICES.get(voice, {}).get("style", "")


def upload(post_id: str, voice: str, out: Path) -> None:
    from . import drive

    root = drive.ensure_folder("voice_samples", drive.FOLDERS["05_assets"])
    folder = drive.ensure_folder(post_id, root)
    fid = drive.upload(out / "reel.mp4", folder, f"{post_id}_{voice}.mp4")
    sample = json.loads((out / "sample.json").read_text(encoding="utf-8"))
    sample.update(voice=voice, drive_file_id=fid, link=drive.web_link(fid), folder_link=drive.web_link(folder, True))
    (out / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    print(sample["link"])


def report(post_id: str, root: Path) -> None:
    import os

    from . import notify

    samples = sorted((json.loads(p.read_text(encoding="utf-8")) for p in root.glob("**/sample.json")),
                     key=lambda s: list(VOICES).index(s["voice"]) if s["voice"] in VOICES else 99)
    if not samples:
        raise SystemExit("no samples found")
    lines = [f"## ナレーション音声の比較（{post_id}）", "",
             "同じ動画を、Geminiの男性ボイス別に作りました。Driveアプリで再生して比べてください。", "",
             "| 声 | 雰囲気 | 動画 | 尺 | 推定費用 |", "|---|---|---|---|---|"]
    for i, s in enumerate(samples, 1):
        label = VOICES.get(s["voice"], {}).get("label", "")
        cost = f"${s['est_cost_usd']:.3f}" if s.get("est_cost_usd") is not None else "—"
        lines.append(f"| {i}. **{s['voice']}** | {label} | [再生]({s['link']}) | {s['duration_sec']:.1f}秒 | {cost} |")
    lines += ["", f"- 使用モデル: `{samples[0].get('model')}`",
              f"- 保存先: {samples[0].get('folder_link')}（`05_動画・音声・アニメーション素材/voice_samples`。承認待ちには入りません）",
              "- 推定費用は音声の長さからの概算です（実際の請求額は Google AI Studio で確認してください）。", "",
              "気に入った声を Claude Code に伝えてください（例:「Charonで本番を作り直して」）。"]
    num = notify.create_issue(f"[声の比較] {post_id} ナレーション3種", "\n".join(lines), ["voice-sample"],
                              os.environ.get("APPROVER_LOGIN"))
    print(f"issue #{num}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "style":
        print(style(sys.argv[2]))
    elif cmd == "upload":
        upload(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
    elif cmd == "report":
        report(sys.argv[2], Path(sys.argv[3]))
