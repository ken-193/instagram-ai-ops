"""Operational commands run by GitHub Actions.

  python -m pipeline.ops submit   <post_id>   # after a QC-passed build: Drive upload + approval request
  python -m pipeline.ops publish  <post_id>   # only after approval: Muse handoff or Instagram API (config/publishing.json)
  python -m pipeline.ops posted   <post_id>   # after /posted: file the Drive folders, close the issue
  python -m pipeline.ops insights             # collect 24h / 72h / 7d metrics for published posts
  python -m pipeline.ops guard    <post_id>   # cost / attempt limits before rendering

Every state change is committed and pushed immediately (git is the audit log).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import notify, state

ROOT = Path(__file__).resolve().parents[1]
LIMITS = json.loads((ROOT / "config/limits.json").read_text())
PUBLISHING = json.loads((ROOT / "config/publishing.json").read_text())
CHECKPOINTS = {"24h": 24, "72h": 72, "7d": 168}


def git_commit(msg: str) -> None:
    """Commit state/ + posts/ docs and push. Raises if the push fails, so callers stop
    before doing anything irreversible on top of an unrecorded state."""
    subprocess.run(["git", "add", "state", "posts", "reports"], cwd=ROOT, check=False)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, check=True)
    for attempt in range(3):
        if subprocess.run(["git", "push"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "pull", "--rebase"], cwd=ROOT, check=True)
    raise RuntimeError("git push failed; state not recorded")


def full_caption(post_dir: Path) -> str:
    return (post_dir / "caption.txt").read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------- guard
def guard(post_id: str) -> None:
    st = state.load(post_id)
    if st["status"] not in state.RERENDERABLE:
        sys.exit(f"{post_id} is {st['status']}; refusing to re-render (use /withdraw first if it must change)")
    if st.get("render_attempts", 0) >= LIMITS["max_render_attempts_per_post"]:
        sys.exit(f"{post_id}: render attempt limit reached ({LIMITS['max_render_attempts_per_post']})")
    ledger = ROOT / "state" / "costs.json"
    costs = json.loads(ledger.read_text()) if ledger.exists() else {}
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    if costs.get(month, 0) >= LIMITS["max_cost_usd_per_month"]:
        sys.exit(f"monthly cost cap reached: {costs[month]} USD")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    built_today = sum(1 for p in state.STATE_DIR.glob("*.json")
                      for h in json.loads(p.read_text())["history"] if h["to"] == "rendered" and h["at"].startswith(today))
    if built_today >= LIMITS["max_productions_per_day"]:
        sys.exit("daily production limit reached")
    st["render_attempts"] = st.get("render_attempts", 0) + 1
    state.save(st)


def record_cost(usd: float) -> None:
    ledger = ROOT / "state" / "costs.json"
    costs = json.loads(ledger.read_text()) if ledger.exists() else {}
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    costs[month] = round(costs.get(month, 0) + usd, 4)
    ledger.write_text(json.dumps(costs, indent=2) + "\n")


# ---------------------------------------------------------------- submit for approval
def narration_check_line(post_dir: Path) -> str:
    p = post_dir / "out/narration_check.json"
    if not p.exists():
        return "- ナレーション読み上げチェック: 未実施"
    r = json.loads(p.read_text(encoding="utf-8"))
    lines = r.get("lines", [])
    ok = sum(1 for x in lines if x.get("ok"))
    exact = sum(1 for x in lines if x.get("exact"))
    return (f"- ナレーション読み上げチェック: {ok}/{len(lines)} 行 OK（完全一致 {exact} 行、音声認識 {r.get('model')}）"
            if lines else "- ナレーション読み上げチェック: ナレーションなし")


def submit(post_id: str) -> None:
    from . import drive

    post_dir = ROOT / "posts" / post_id
    meta = json.loads((post_dir / "metadata.json").read_text(encoding="utf-8"))
    if not meta.get("qc_passed"):
        raise SystemExit("QC did not pass; not sending for approval")
    st = state.load(post_id)
    if st["status"] not in state.RERENDERABLE:  # checked before touching Drive or the issue
        raise SystemExit(f"{post_id} is {st['status']}; not replacing an approved/queued version")
    if st["status"] in ("drafted", "revision_requested", "failed"):
        state.transition(st, "rendered", "pipeline", "build + QC passed")
    if st["status"] == "pending_approval":  # re-render while waiting: replace the version under review
        state.transition(st, "rendered", "pipeline", "new render replaces pending version")
    st["revision"] = st.get("revision", 0) + 1
    record_cost(meta.get("cost_usd") or 0.0)

    # reuse the folder recorded for this post (it may have been renamed, e.g. "_承認済み");
    # look up by name only the first time
    folder = st.get("drive", {}).get("folder_id") or drive.ensure_folder(post_id, drive.FOLDERS["06_pending"])
    files = {}
    for name, src in [("reel.mp4", post_dir / "out/reel.mp4"), ("thumbnail.jpg", post_dir / "out/thumbnail.jpg"),
                      ("script.md", post_dir / "script.md"), ("script.json", post_dir / "script.json"),
                      ("caption.txt", post_dir / "caption.txt"), ("sources.md", post_dir / "sources.md"),
                      ("metadata.json", post_dir / "metadata.json"), ("quality_check.md", post_dir / "quality_check.md")]:
        if name in ("script.md", "script.json") and not src.exists():  # 3D posts (studio3d) have no 2D script
            continue
        files[name] = drive.upload(src, folder, name)
    extras = [("narration_check.md", post_dir / "out/narration_check.md"),
              ("subtitles.srt", post_dir / "out/subtitles.srt"), ("narration.wav", post_dir / "out/narration.wav"),
              ("bgm_sfx.wav", post_dir / "out/bgm_sfx.wav"), ("ai_video_prompts.md", post_dir / "ai_video_prompts.md")]
    for name, src in extras:  # optional deliverables (not part of what Muse posts)
        if src.exists():
            files[name] = drive.upload(src, folder, name)
    clips = sorted((post_dir / "out/scenes").glob("*.mp4"))
    if clips:
        sub = drive.ensure_folder("scenes", folder)
        for c in clips:
            files["scenes/" + c.name] = drive.upload(c, sub, c.name)
    st["drive"] = {"folder_id": folder, "files": files}
    st["reel_sha256"] = meta["reel_sha256"]

    sp = post_dir / "script.json"
    title = json.loads(sp.read_text(encoding="utf-8"))["title"] if sp.exists() else meta["title"]
    body = "\n".join([
        f"## {title}", "",
        f"- 投稿ID: `{post_id}` / 版: rev {st['revision']} / 尺: {meta['duration_sec']:.1f}秒",
        f"- 動画（iPhoneのDriveアプリで再生）: {drive.web_link(files['reel.mp4'])}",
        f"- フォルダ: {drive.web_link(folder, folder=True)}",
        f"- reel sha256: `{meta['reel_sha256'][:16]}…`（承認はこのファイルに紐づきます）",
        narration_check_line(post_dir), "",
        "### キャプション", "", "```", full_caption(post_dir), "```", "",
        "### 返信で操作（オーナーのみ有効）", "",
        "- `/approve` … この版を承認して公開", "- `/revise 修正内容` … 修正して作り直し", "- `/reject 理由` … 却下（公開しない）", "",
        "未承認の動画は公開されません。誤って二重に送信しても、2回目以降は状態チェックで無視されます。",
    ])
    if st.get("issue_number"):
        notify.issue_comment(st["issue_number"], "🔁 新しい版を作成しました。\n\n" + body)
    else:
        st["issue_number"] = notify.create_issue(f"[承認待ち] {post_id} {title}", body, ["approval"],
                                                 os.environ.get("APPROVER_LOGIN"))
    state.transition(st, "pending_approval", "pipeline", f"rev {st['revision']} sent for review")
    state.save(st)
    git_commit(f"{post_id}: rev {st['revision']} pending approval")
    notify.push(f"承認待ち: {title}", "GitHubアプリで確認して /approve /revise /reject を返信",
                f"https://github.com/{os.environ.get('GITHUB_REPOSITORY')}/issues/{st['issue_number']}")


# ---------------------------------------------------------------- publish
def _sha256(p: Path) -> str:
    from .build import sha256
    return sha256(p)


def _finalize(st: dict, media_id: str, actor="pipeline") -> None:
    from . import drive, instagram

    m = instagram.media(media_id)
    state.transition(st, "published", actor, "published to Instagram",
                     ig={**st.get("ig", {}), "media_id": media_id, "permalink": m.get("permalink"),
                         "published_at": m.get("timestamp") or state.now()})
    state.save(st)
    git_commit(f"{st['post_id']}: published {m.get('permalink')}")
    try:
        drive.move(st["drive"]["folder_id"], drive.FOLDERS["07_published"])
    except Exception as e:  # moving the folder is bookkeeping; never fail a successful publish over it
        print("drive move failed:", e)
    if st.get("issue_number"):
        notify.issue_comment(st["issue_number"], f"🎉 公開しました: {m.get('permalink')}\nmedia id: `{media_id}`")
        notify.close_issue(st["issue_number"])
    notify.push("公開しました", m.get("permalink") or media_id, m.get("permalink"))


def reconcile(st: dict) -> None:
    """Resolve publishing/publish_unknown without ever creating a second container."""
    from . import instagram

    cid = st.get("ig", {}).get("container_id")
    if not cid:
        state.transition(st, "publish_failed", "pipeline", "no container was created; safe to retry with /approve")
        state.save(st)
        git_commit(f"{st['post_id']}: publish failed before container creation")
        return
    code = instagram.container_status(cid).get("status_code")
    if code == "PUBLISHED":
        cap = (st.get("caption_head") or "")[:40]
        match = next((m for m in instagram.recent_media(25) if cap and (m.get("caption") or "").startswith(cap)), None)
        if match:
            _finalize(st, match["id"])
            return
        if st["status"] == "publishing":
            state.transition(st, "publish_unknown", "pipeline", "container PUBLISHED but media not matched")
        st.setdefault("notes", []).append("Instagramアプリで公開済みか確認し、media idを手動で記録してください")
    elif code == "FINISHED":
        _finalize(st, instagram.publish(cid))  # container is single-use: this cannot duplicate
        return
    else:
        if st["status"] == "publishing":
            state.transition(st, "publish_unknown", "pipeline", f"container status {code}")
    state.save(st)
    git_commit(f"{st['post_id']}: publish state needs attention ({code})")
    notify.push("公開状態の確認が必要", f"{st['post_id']}: {code}", priority="high")
    raise SystemExit(f"publish state unresolved: {code}")


def handoff(post_id: str) -> None:
    """Muse mode: copy the APPROVED reel + caption + cover into Drive 11_Muse投稿キュー.
    Only this step ever writes to the folder Muse watches, and only for status `approved`
    with the exact approved file, so Muse can never pick up an unapproved video."""
    from . import drive

    st = state.load(post_id)
    if st["status"] in ("handed_off", "published"):
        print(f"already {st['status']}; nothing to do")
        return
    work = ROOT / ".cache" / "publish"
    work.mkdir(parents=True, exist_ok=True)
    reel = drive.download(st["drive"]["files"]["reel.mp4"], work / f"{post_id}.mp4")
    state.assert_publishable(st, LIMITS["max_publish_attempts_per_post"], _sha256(reel))

    cfg = PUBLISHING["muse"]
    queue = drive.FOLDERS[cfg["queue_folder_key"]]
    stem = cfg["file_stem"].format(post_id=post_id)
    copied = {}
    for src, ext in cfg["files"].items():
        copied[src] = drive.copy(st["drive"]["files"][src], queue, stem + ext)
    st["muse"] = {"queue_folder_id": queue, "files": copied, "handed_off_at": state.now()}
    state.transition(st, "handed_off", "pipeline", "copied to 11_Muse投稿キュー")
    state.save(st)
    git_commit(f"{post_id}: handed off to Muse")
    try:
        drive.rename(st["drive"]["folder_id"], f"{post_id}_承認済み")
    except Exception as e:  # cosmetic only
        print("rename failed:", e)
    if st.get("issue_number"):
        notify.issue_comment(st["issue_number"], "\n".join([
            "📦 Museの投稿キューに置きました（Drive `11_Muse投稿キュー`）。",
            "", *[f"- `{stem + ext}`" for ext in cfg["files"].values()], "",
            "Museで投稿できたら、このIssueに `/posted 投稿のURL` と返信してください。",
            "例: `/posted https://www.instagram.com/reel/xxxxxxxx/`",
            "記録すると、キューのファイルは投稿済みフォルダへ移動します（Museが同じ動画を二度投稿しないように）。"]))
    notify.push("Muse投稿キューに追加", f"{post_id} を投稿できます")


def withdraw(post_id: str) -> None:
    """After /withdraw: take the queued files out of 11_Muse投稿キュー so Muse cannot post them."""
    from . import drive

    st = state.load(post_id)
    if st["status"] != "revision_requested" or not st.get("withdrawals"):
        raise SystemExit(f"{post_id} was not withdrawn")
    w = st["withdrawals"][-1]
    for fid in (w.get("muse") or {}).get("files", {}).values():
        drive.move(fid, st["drive"]["folder_id"])
    drive.rename(st["drive"]["folder_id"], post_id)
    st["muse"] = None
    state.save(st)
    git_commit(f"{post_id}: withdrawn from Muse queue")
    if st.get("issue_number"):
        notify.issue_comment(st["issue_number"], "↩️ Museの投稿キューから取り下げました（キューのファイルは投稿フォルダへ移動済み）。"
                                                 "修正版を作成すると、新しい承認依頼が届きます。")


def posted(post_id: str) -> None:
    """After /posted: move queue files out of Muse's folder (no double post) and file everything in 07."""
    from . import drive

    st = state.load(post_id)
    if st["status"] != "published":
        raise SystemExit(f"{post_id} is {st['status']}, not published")
    done = drive.FOLDERS["07_published"]
    drive.move(st["drive"]["folder_id"], done)
    drive.rename(st["drive"]["folder_id"], post_id)
    for fid in st.get("muse", {}).get("files", {}).values():
        drive.move(fid, st["drive"]["folder_id"])
    if st.get("issue_number"):
        notify.close_issue(st["issue_number"])


def publish(post_id: str) -> None:
    if PUBLISHING.get("mode") == "muse":
        handoff(post_id)
        return
    from . import drive, instagram

    st = state.load(post_id)
    if st["status"] == "published":
        print("already published; nothing to do")
        return
    if st["status"] in ("publishing", "publish_unknown"):
        reconcile(st)
        return
    work = ROOT / ".cache" / "publish"
    work.mkdir(parents=True, exist_ok=True)
    reel = drive.download(st["drive"]["files"]["reel.mp4"], work / f"{post_id}.mp4")
    state.assert_publishable(st, LIMITS["max_publish_attempts_per_post"], _sha256(reel))

    lim = instagram.publishing_limit()
    print("publishing limit:", lim)
    caption = full_caption(ROOT / "posts" / post_id)
    st["publish_attempts"] = st.get("publish_attempts", 0) + 1
    st["caption_head"] = caption[:40]
    state.transition(st, "publishing", "pipeline", f"attempt {st['publish_attempts']}")
    state.save(st)
    git_commit(f"{post_id}: publishing")  # recorded BEFORE touching Instagram

    try:
        cid = instagram.create_reel_container(caption)
        st["ig"] = {**st.get("ig", {}), "container_id": cid}
        state.save(st)
        git_commit(f"{post_id}: container {cid}")
        instagram.upload_video(cid, reel)
        instagram.wait_finished(cid)
        media_id = instagram.publish(cid)
    except Exception as e:
        print("publish error:", e)
        st.setdefault("errors", []).append({"at": state.now(), "error": str(e)[:500]})
        state.save(st)
        reconcile(st)
        return
    _finalize(st, media_id)


# ---------------------------------------------------------------- insights
def collect_insights() -> list[str]:
    from . import instagram

    done = []
    nowt = datetime.now(timezone.utc)
    for p in sorted(state.STATE_DIR.glob("*.json")):
        st = json.loads(p.read_text(encoding="utf-8"))
        ig = st.get("ig", {})
        if st["status"] != "published" or not ig.get("media_id"):
            continue
        pub = datetime.fromisoformat(ig["published_at"].replace("Z", "+00:00").replace("+0000", "+00:00"))
        age_h = (nowt - pub).total_seconds() / 3600
        for key, hours in CHECKPOINTS.items():
            if age_h >= hours and key not in st.setdefault("insights", {}):
                st["insights"][key] = {"collected_at": state.now(), "age_hours": round(age_h, 1),
                                       "metrics": instagram.insights(ig["media_id"])}
                done.append(f"{st['post_id']}:{key}")
        state.save(st)
    if done:
        from .analyze import write_reports
        write_reports()
        git_commit("insights: " + ", ".join(done))
    return done


def main(argv=None):
    argv = argv or sys.argv[1:]
    cmd = argv[0]
    if cmd == "submit":
        submit(argv[1])
    elif cmd == "publish":
        publish(argv[1])
    elif cmd == "posted":
        posted(argv[1])
    elif cmd == "withdraw":
        withdraw(argv[1])
    elif cmd == "insights":
        print(collect_insights())
    elif cmd == "guard":
        guard(argv[1])
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
