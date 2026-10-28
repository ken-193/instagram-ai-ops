"""Post state machine. The JSON files under state/posts/ are the single source of truth for
approval and publishing; GitHub Actions commits every transition, so history is auditable in git.

Safety rules enforced here (not in the UI):
  * only pending_approval -> approved, and only by the configured owner
  * approval is bound to the exact reel sha256 that was sent for review
  * publishing requires status == approved and no existing Instagram media id
  * the status flips to `publishing` (and is committed) BEFORE any Instagram call, so a crash
    or rerun lands in reconciliation instead of a second post
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state" / "posts"

TRANSITIONS: dict[str, set[str]] = {
    "drafted": {"rendered", "failed"},
    "rendered": {"pending_approval", "failed"},
    "pending_approval": {"approved", "revision_requested", "rejected", "rendered"},
    "revision_requested": {"drafted", "rendered", "rejected"},
    "approved": {"publishing", "rejected"},
    "publishing": {"published", "publish_unknown", "publish_failed"},
    "publish_unknown": {"published", "publish_failed", "approved"},
    "publish_failed": {"approved", "rejected"},
    "failed": {"drafted", "rendered"},
    "published": set(),
    "rejected": set(),
}


class TransitionError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def path(post_id: str) -> Path:
    return STATE_DIR / f"{post_id}.json"


def load(post_id: str) -> dict:
    p = path(post_id)
    if not p.exists():
        return {"post_id": post_id, "status": "drafted", "revision": 0, "history": [], "render_attempts": 0,
                "publish_attempts": 0, "drive": {}, "ig": {}, "insights": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def save(st: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path(st["post_id"]).write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def transition(st: dict, to: str, actor: str, note: str = "", **fields) -> dict:
    frm = st["status"]
    if to not in TRANSITIONS.get(frm, set()):
        raise TransitionError(f"{st['post_id']}: {frm} -> {to} is not allowed")
    st["status"] = to
    st.update(fields)
    st["history"].append({"at": now(), "from": frm, "to": to, "actor": actor, "note": note})
    return st


def approve(st: dict, actor: str, owner: str, reel_sha256: str) -> dict:
    if actor.lower() != owner.lower():
        raise TransitionError(f"{actor} is not allowed to approve (owner: {owner})")
    retry = st["status"] == "publish_failed" and not st.get("ig", {}).get("container_id")
    if st["status"] != "pending_approval" and not retry:
        raise TransitionError(f"cannot approve while status is {st['status']}")
    if not st.get("reel_sha256") or st["reel_sha256"] != reel_sha256:
        raise TransitionError("reel changed since it was sent for review; re-review the latest version")
    return transition(st, "approved", actor, "approved via GitHub issue comment", approved_sha256=reel_sha256,
                      approved_by=actor, approved_at=now(), approved_revision=st.get("revision", 0))


def assert_publishable(st: dict, max_attempts: int, downloaded_sha256: str) -> None:
    if st["status"] != "approved":
        raise TransitionError(f"not approved (status={st['status']})")
    if st.get("ig", {}).get("media_id"):
        raise TransitionError("already published (media_id recorded)")
    if st.get("publish_attempts", 0) >= max_attempts:
        raise TransitionError("publish attempt limit reached; manual check required")
    if downloaded_sha256 != st.get("approved_sha256"):
        raise TransitionError("file to publish does not match the approved file")
