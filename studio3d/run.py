"""Render a 世界の仕様外 project scene by scene, in frame chunks.

  python studio3d/run.py matrix <project> [--quality final|draft]           # JSON list of render chunks
  python studio3d/run.py render <project> <scene_id> --start A --end B [--quality final]

Runs with Blender's Python module (`pip install bpy`). Each scene file in 04_blender/ defines
  SECONDS = 5.0
  def build(ctx) -> dict          # create the 3D scene once, return handles
  def pose(ctx, h, t)             # put everything where it is at scene time t (pure function of t)
Frames go to studio3d/projects/<project>/05_render/frames/<scene_id>/0000.png ...
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))


def project(name: str) -> dict:
    p = HERE / "projects" / name / "04_blender" / "project.json"
    return json.loads(p.read_text(encoding="utf-8"))


def preset(quality: str) -> dict:
    cfg = json.loads((HERE / "config" / "render.json").read_text(encoding="utf-8"))
    return {**cfg["presets"][quality], "fps": cfg["fps"], "chunk": cfg["chunk_frames"]}


def matrix(name: str, quality: str) -> list[dict]:
    pr, ps = project(name), preset(quality)
    out = []
    for sc in pr["scenes"]:
        n = int(round(sc["seconds"] * ps["fps"]))
        for a in range(0, n, ps["chunk"]):
            out.append({"scene": sc["id"], "start": a, "end": min(n, a + ps["chunk"])})
    return out


def render(name: str, scene_id: str, start: int, end: int, quality: str) -> None:
    from studio3d.lib import core
    pr, ps = project(name), preset(quality)
    sc = next(s for s in pr["scenes"] if s["id"] == scene_id)
    path = HERE / "projects" / name / "04_blender" / sc["file"]
    spec = importlib.util.spec_from_file_location(f"scene_{scene_id}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if abs(mod.SECONDS - sc["seconds"]) > 1e-6:
        raise SystemExit(f"{sc['file']}: SECONDS={mod.SECONDS} but project.json says {sc['seconds']}")
    bscene = core.setup(ps["width"], ps["height"], ps["fps"], ps["samples"])
    ctx = {"fps": ps["fps"], "seconds": sc["seconds"], "quality": quality, "project": pr}
    handles = mod.build(ctx)
    out = HERE / "projects" / name / "05_render" / "frames" / scene_id
    out.mkdir(parents=True, exist_ok=True)
    n = int(round(sc["seconds"] * ps["fps"]))
    for f in range(start, min(end, n)):
        mod.pose(ctx, handles, f / ps["fps"])
        bscene.render.filepath = str(out / f"{f:04d}.png")
        t0 = time.time()
        import bpy
        bpy.ops.render.render(write_still=True)
        print(f"{scene_id} frame {f}/{n} {time.time() - t0:.1f}s", flush=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["matrix", "render"])
    ap.add_argument("project")
    ap.add_argument("scene", nargs="?")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10 ** 6)
    ap.add_argument("--quality", default="final")
    a = ap.parse_args(argv)
    if a.cmd == "matrix":
        m = matrix(a.project, a.quality)
        line = "matrix=" + json.dumps({"include": m})
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(line + "\n")
        print(line)
    else:
        render(a.project, a.scene, a.start, a.end, a.quality)


if __name__ == "__main__":
    main()
