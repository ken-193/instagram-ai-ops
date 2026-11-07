"""Send a finished studio3d reel into the normal approval flow (approval issue -> /approve -> Muse queue).

  python -m studio3d.submit <project> <post_id>

Reads studio3d/projects/<project>/07_final (final mp4, qc.json, narration_check.json from the assemble job)
and writes posts/<post_id>/out/{reel.mp4, thumbnail.jpg, narration_check.*}, metadata.json and
quality_check.md. posts/<post_id>/caption.txt, sources.md and post.json (hook, categories, ending, cover_at)
are written by hand and checked in (project.json is not touched: editing it would re-render the whole video).
Then `python -m pipeline.ops submit <post_id>` uploads to Drive 06_承認待ち and opens the approval issue,
exactly like a 2D reel. Nothing here touches 11_Muse投稿キュー: only an approved version is copied there.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def main(argv=None):
    argv = argv or sys.argv[1:]
    project, post_id = argv[0], argv[1]
    sys.path.insert(0, str(ROOT))
    from pipeline.build import sha256
    pdir = HERE / "projects" / project
    fin = pdir / "07_final"
    pr = json.loads((pdir / "04_blender" / "project.json").read_text(encoding="utf-8"))
    qc = json.loads((fin / "qc.json").read_text(encoding="utf-8"))
    post = ROOT / "posts" / post_id
    out = post / "out"
    out.mkdir(parents=True, exist_ok=True)
    for f in ("caption.txt", "sources.md", "post.json"):
        if not (post / f).exists():
            raise SystemExit(f"posts/{post_id}/{f} is missing (write the caption / sources first)")
    if not qc["passed"]:
        raise SystemExit("QC did not pass; not sending for approval")
    reel = out / "reel.mp4"
    shutil.copyfile(fin / f"{project}_final.mp4", reel)
    info = json.loads((post / "post.json").read_text(encoding="utf-8"))
    total = sum(s["seconds"] for s in pr["scenes"])
    cover_at = info.get("cover_at", total - 3.5)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{cover_at:.2f}", "-i", str(reel), "-frames:v", "1",
                    "-q:v", "2", str(out / "thumbnail.jpg")], check=True)
    nc = fin / "narration_check.json"
    if nc.exists():
        rows = json.loads(nc.read_text(encoding="utf-8"))
        (out / "narration_check.json").write_text(json.dumps({"post_id": post_id, "model": "medium", "lines": rows},
                                                             ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copyfile(fin / "narration_check.md", out / "narration_check.md")
    acfg = json.loads((pdir / "04_blender" / "audio.json").read_text(encoding="utf-8")) if (pdir / "04_blender" / "audio.json").exists() else {}
    meta = {
        "post_id": post_id, "title": pr["title"], "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duration_sec": total, "source": f"studio3d/{project}", "quality": qc.get("quality"),
        "tts_backend": acfg.get("tts", {}).get("backend"), "tts_options": acfg.get("tts", {}),
        "tts_credit": "ナレーション音声: 音読さん（ondoku3.com）" if acfg.get("tts", {}).get("backend") == "ondoku" else None,
        "render": {"engine": "Blender (Cycles) via studio3d", "fps": 30, "size": "1080x1920"},
        "reel_sha256": sha256(reel), "reel_bytes": reel.stat().st_size, "qc_passed": True, "cost_usd": 0.0,
        "categories": info.get("categories", ["fiction"]), "hook": info.get("hook"),
        "tokushima_ending_type": info.get("tokushima_ending_type"),
    }
    (post / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = "\n".join(f"- {'✅' if c['ok'] else '❌'} {c['check']}: {c['detail']}" for c in qc["checks"])
    (post / "quality_check.md").write_text(f"# 品質チェック（studio3d: {project}）\n\n{rows}\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
