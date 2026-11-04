"""Pre-rendered 3D hero clips (Blender) used as backgrounds by some scenes.

  python -m pipeline.clips encode <post_id> <shot> <frames_dir> <out.mp4>   # frames -> 1080x1920 mp4
  python -m pipeline.clips upload <post_id> <shot> <out.mp4>                # Drive 05/3d_clips/<post_id>, record in clips.json
  python -m pipeline.clips fetch <post_id>                                  # produce: download + verify + extract frames

posts/<id>/clips.json : {"<shot>": {"file_id": ..., "sha256": ..., "fps": 30, "frames": N}}
Frames are extracted to posts/<id>/clips/<shot>/0000.png ... (not committed).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(post_id: str) -> dict:
    p = ROOT / "posts" / post_id / "clips.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def encode(post_id: str, shot: str, frames: Path, out: Path, fps: int = 30) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "%04d.png"),
                    "-vf", "scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-crf", "14", "-preset", "slow",
                    "-pix_fmt", "yuv420p", str(out)], check=True)


def upload(post_id: str, shot: str, mp4: Path) -> None:
    from . import drive

    root = drive.ensure_folder("3d_clips", drive.FOLDERS["05_assets"])
    folder = drive.ensure_folder(post_id, root)
    fid = drive.upload(mp4, folder, f"{shot}.mp4")
    frames = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                                 "stream=nb_read_frames", "-of", "csv=p=0", str(mp4)], capture_output=True, text=True,
                                check=True).stdout.strip())
    m = manifest(post_id)
    m[shot] = {"file_id": fid, "sha256": _sha(mp4), "fps": 30, "frames": frames}
    (ROOT / "posts" / post_id / "clips.json").write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(m[shot]))


def fetch(post_id: str) -> None:
    from . import drive

    for shot, info in manifest(post_id).items():
        d = ROOT / "posts" / post_id / "clips" / shot
        d.mkdir(parents=True, exist_ok=True)
        mp4 = d.parent / f"{shot}.mp4"
        drive.download(info["file_id"], mp4)
        if _sha(mp4) != info["sha256"]:
            raise SystemExit(f"3D clip {shot}: sha256 mismatch (Drive file changed?)")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-start_number", "0", str(d / "%04d.png")],
                       check=True)
        print(f"{shot}: {len(list(d.glob('*.png')))} frames")


@lru_cache(maxsize=8)
def _frames(post_dir: str, shot: str) -> tuple:
    d = Path(post_dir) / "clips" / shot
    return tuple(sorted(d.glob("*.png"))) if d.exists() else ()


def frame(post_dir, shot: str, t: float, fps: int = 30):
    """PIL image of the clip frame at scene time t, or None when the clip isn't available (falls back to 2.5D)."""
    if post_dir is None:
        return None
    fr = _frames(str(post_dir), shot)
    if not fr:
        return None
    from PIL import Image
    return Image.open(fr[max(0, min(len(fr) - 1, int(t * fps)))]).convert("RGBA")


if __name__ == "__main__":
    cmd, pid = sys.argv[1], sys.argv[2]
    if cmd == "encode":
        encode(pid, sys.argv[3], Path(sys.argv[4]), Path(sys.argv[5]))
    elif cmd == "upload":
        upload(pid, sys.argv[3], Path(sys.argv[4]))
    elif cmd == "fetch":
        fetch(pid)
