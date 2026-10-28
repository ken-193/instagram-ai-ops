"""Operational commands run by GitHub Actions.

  python -m pipeline.ops submit   <post_id>   # after a QC-passed build: Drive upload + approval request
  python -m pipeline.ops publish  <post_id>   # only after approval; idempotent, reconciles unknown states
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
    if st["status"] in ("published", "publishing", "approved"):
        sys.exit(f"{post_id} is {st['status']}; refusing to re-render")
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
def submit(post_id: str) -> None:
    from . import drive

    post_dir = ROOT / "posts" / post_id
    meta = json.loads((post_dir / "metadata.json").read_text(encoding="utf-8"))
    if not meta.get("qc_passed"):
        raise SystemExit("QC did not pass; not sending for approval")
    st = state.load(post_id)
    if st["status"] in ("drafted", "revision_requested", "failed"):
        state.transition(st, "rendered", "pipeline", "build + QC passed")
    if st["status"] == "pending_approval":  # re-render while waiting: replace the version under review
        state.transition(st, "rendered", "pipeline", "new render replaces pending version")
    st["revision"] = st.get("revision", 0) + 1
    record_cost(meta.get("cost_usd") or 0.0)

    folder = drive.ensure_folder(post_id, drive.FOLDERS["06_pending"])
    files = {}
    for name, src in [("reel.mp4", post_dir / "out/reel.mp4"), ("thumbnail.jpg", post_dir / "out/thumbnail.jpg"),
                      ("script.md", post_dir / "script.md"), ("script.json", post_dir / "script.json"),
                      ("caption.txt", post_dir / "caption.txt"), ("sources.md", post_dir / "sources.md"),
                      ("metadata.json", post_dir / "metadata.json"), ("quality_check.md", post_dir / "quality_check.md")]:
        files[name] = drive.upload(src, folder, name)
    st["drive"] = {"folder_id": folder, "files": files}
    st["reel_sha256"] = meta["reel_sha256"]

    script = json.loads((post_dir / "script.json").read_text(encoding="utf-8"))
    body = "\n".join([
        f"## {script['title']}", "",
        f"- 投稿ID: `{post_id}` / 版: rev {st['revision']} / 尺: {meta['duration_sec']:.1f}秒",
        f"- 動画（iPhoneのDriveアプリで再生）: {drive.web_link(files['reel.mp4'])}",
        f"- フォルダ: {drive.web_link(folder, folder=True)}",
        f"- reel sha256: `{meta['reel_sha256'][:16]}…`（承認はこのファイルに紐づきます）", "",
        "### キャプション", "", "```", full_caption(post_dir), "```", "",
        "### 返信で操作（オーナーのみ有効）", "",
        "- `/approve` … この版を承認して公開", "- `/revise 修正内容` … 修正して作り直し", "- `/reject 理由` … 却下（公開しない）", "",
        "未承認の動画は公開されません。誤って二重に送信しても、2回目以降は状態チェックで無視されます。",
    ])
    if st.get("issue_number"):
        notify.issue_comment(st["issue_number"], "🔁 新しい版を作成しました。\n\n" + body)
    else:
        st["issue_number"] = notify.create_issue(f"[承認待ち] {post_id} {script['title']}", body, ["approval"],
                                                 os.environ.get("APPROVER_LOGIN"))
    state.transition(st, "pending_approval", "pipeline", f"rev {st['revision']} sent for review")
    state.save(st)
    git_commit(f"{post_id}: rev {st['revision']} pending approval")
    notify.push(f"承認待ち: {script['title']}", "GitHubアプリで確認して /approve /revise /reject を返信",
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


def publish(post_id: str) -> None:
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
    elif cmd == "insights":
        print(collect_insights())
    elif cmd == "guard":
        guard(argv[1])
    else:
        raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
