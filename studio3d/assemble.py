"""Turn rendered frames into the final reel, check it, and save everything to Google Drive.

  python -m studio3d.assemble <project> [--quality final] [--no-upload]

Steps: frames -> one mp4 per scene (05_render) -> concatenated final mp4 (07_final) -> soundtrack if the
project has 04_blender/audio.json (narration + effects + BGM, narration readback check) -> automatic checks
(resolution, fps, duration, codec, audio, no black / frozen frames) -> contact sheet (one still per scene) ->
upload to Drive instagram_reel_post/01_projects/<project>/... and a copy of the final to 03_completed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import audio3d

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(" ".join(map(str, cmd)) + "\n" + r.stderr[-800:])
    return r


def encode_scene(frames: Path, out: Path, fps: int, width: int, height: int):
    vf = f"scale={width}:{height}:flags=lanczos"
    run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", "0", "-i", str(frames / "%04d.png"),
         "-vf", vf, "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(fps), str(out)])


def concat(parts: list[Path], out: Path):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
         "-movflags", "+faststart", str(out)])
    lst.unlink()


def probe(p: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)])
    return json.loads(r.stdout)


def qc(final: Path, expect_seconds: float, fps: int, expect_audio: bool = False) -> dict:
    info = probe(final)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    dur = float(info["format"]["duration"])
    num, den = v["r_frame_rate"].split("/")
    checks = [
        ("1080x1920 (9:16)", (v["width"], v["height"]) == (1080, 1920), f"{v['width']}x{v['height']}"),
        (f"{fps} fps", abs(float(num) / float(den) - fps) < 0.01, v["r_frame_rate"]),
        ("H.264 / yuv420p", v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p", f"{v['codec_name']} {v['pix_fmt']}"),
        ("duration matches the plan", abs(dur - expect_seconds) < 0.3, f"{dur:.2f}s / plan {expect_seconds:.2f}s"),
    ]
    if expect_audio:
        a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
        checks.append(("audio track (AAC)", bool(a) and a["codec_name"] == "aac",
                       f"{a['codec_name']} {a.get('channels')}ch" if a else "no audio"))
    bd = subprocess.run(["ffmpeg", "-i", str(final), "-vf", "blackdetect=d=0.3:pix_th=0.05", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    checks.append(("no black segments", "black_start" not in bd, "ok" if "black_start" not in bd else "black detected"))
    fz = subprocess.run(["ffmpeg", "-i", str(final), "-vf", "freezedetect=n=0.0005:d=1.5", "-an", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    checks.append(("no frozen segments > 1.5s", "freeze_start" not in fz, "ok" if "freeze_start" not in fz else "freeze detected"))
    return {"passed": all(c[1] for c in checks), "checks": [{"check": c[0], "ok": c[1], "detail": c[2]} for c in checks]}


def contact_sheet(scene_mp4s: list[Path], out: Path):
    """One still from the middle of each scene, side by side (quick review on a phone)."""
    from PIL import Image
    tiles = []
    for p in scene_mp4s:
        dur = float(probe(p)["format"]["duration"])
        png = p.with_suffix(".mid.png")
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{dur / 2:.2f}", "-i", str(p), "-frames:v", "1", str(png)])
        tiles.append(Image.open(png).convert("RGB").resize((360, 640)))
        png.unlink()
    sheet = Image.new("RGB", (360 * len(tiles), 640), (20, 20, 20))
    for i, im in enumerate(tiles):
        sheet.paste(im, (i * 360, 0))
    sheet.save(out, quality=88)


def upload(name: str, pdir: Path, files: dict[str, list[Path]], final: Path) -> dict:
    sys.path.insert(0, str(ROOT))
    from pipeline import drive
    cfg = json.loads((HERE / "config" / "drive.json").read_text(encoding="utf-8"))
    proj = drive.ensure_folder(name, cfg["projects"])
    links = {"project_folder": drive.web_link(proj, folder=True)}
    sub = {s: drive.ensure_folder(s, proj) for s in cfg["project_subfolders"]}
    for folder, paths in files.items():
        for p in paths:
            fid = drive.upload(p, sub[folder], p.name)
            if p == final:
                links["final"] = drive.web_link(fid)
    links["completed"] = drive.web_link(drive.upload(final, cfg["completed"], f"{name}.mp4"))
    return links


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--quality", default="final")
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--whisper-model", default="medium")
    ap.add_argument("--skip-readback", action="store_true", help="local tests only: skip the Whisper check")
    a = ap.parse_args(argv)
    pdir = HERE / "projects" / a.project
    pr = json.loads((pdir / "04_blender" / "project.json").read_text(encoding="utf-8"))
    rc = json.loads((HERE / "config" / "render.json").read_text(encoding="utf-8"))
    fps = rc["fps"]
    rend, fin = pdir / "05_render", pdir / "07_final"
    rend.mkdir(parents=True, exist_ok=True)
    fin.mkdir(parents=True, exist_ok=True)
    parts = []
    for sc in pr["scenes"]:
        frames = rend / "frames" / sc["id"]
        n = len(list(frames.glob("*.png")))
        want = int(round(sc["seconds"] * fps))
        if n != want:
            raise SystemExit(f"{sc['id']}: {n} frames rendered, {want} expected")
        out = rend / f"{a.project}_{sc['id']}.mp4"
        if sc.get("hud"):                                   # on-screen text drawn on the upscaled frames
            from . import hud
            lay = rend / "hud" / sc["id"]
            hud.apply(frames, lay, fps, sc["hud"], pr.get("series", {}))
            frames = lay
        encode_scene(frames, out, fps, 1080, 1920)
        parts.append(out)
    final = fin / f"{a.project}_final.mp4"
    cfg = audio3d.load(pdir)
    extra = []
    if cfg:
        silent = fin / f"{a.project}_picture.mp4"
        concat(parts, silent)
        aud = pdir / "06_audio"
        aud.mkdir(parents=True, exist_ok=True)
        stereo, rows = audio3d.build(pr, cfg, ROOT / ".cache" / "tts")
        sys.path.insert(0, str(ROOT))
        from pipeline import audio as amod
        wav = aud / f"{a.project}_mix.wav"
        amod.write_wav(wav, stereo)
        if not a.skip_readback:
            ok, md = audio3d.readback_check(rows, fin, a.whisper_model)
            print(md)
            if not ok:
                raise SystemExit("narration readback check failed: not uploading")
            extra = [fin / "narration_check.md"]
        audio3d.mux(silent, wav, final)
        silent.unlink()
    else:
        concat(parts, final)
    report = qc(final, sum(s["seconds"] for s in pr["scenes"]), fps, expect_audio=bool(cfg))
    report["quality"] = a.quality
    (fin / "qc.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    contact_sheet(parts, fin / f"{a.project}_contact_sheet.jpg")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        raise SystemExit("QC failed: not uploading")
    if a.no_upload:
        return
    docs = {k: sorted(p for p in (pdir / k).glob("*") if p.is_file()) for k in ("01_planning", "02_script", "03_storyboard")}
    files = {**docs, "04_blender": sorted((pdir / "04_blender").glob("*.py")) + [pdir / "04_blender" / "project.json"],
             "05_render": parts, "07_final": [final, fin / "qc.json", fin / f"{a.project}_contact_sheet.jpg"] + extra}
    if cfg:
        files["04_blender"].append(pdir / "04_blender" / "audio.json")
    links = upload(a.project, pdir, files, final)
    (fin / "links.json").write_text(json.dumps(links, indent=2), encoding="utf-8")
    print(json.dumps(links, indent=2))


if __name__ == "__main__":
    main()
