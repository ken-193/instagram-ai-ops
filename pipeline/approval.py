"""Handle approval commands posted as GitHub issue comments (from the GitHub iPhone app).

  /approve            -> approve the version currently under review
  /revise <指示>       -> request changes (recorded; re-render follows)
  /reject <理由>       -> reject; never published
  /posted <URL>       -> owner confirms Muse posted it (records the Instagram URL)

Invoked by .github/workflows/approval.yml with the event payload. Writes GITHUB_OUTPUT
`approved=true|false` and `post_id=...` so the publish job only runs after a valid approval.
"""
from __future__ import annotations

import json
import os
import re
import sys

from . import notify, state

POST_RE = re.compile(r"IG-\d{8}-\d{3}")


def parse_command(body: str) -> tuple[str, str] | None:
    for line in body.strip().splitlines():
        m = re.match(r"^\s*/(approve|revise|reject|posted)\b\s*(.*)$", line.strip(), re.I)
        if m:
            return m.group(1).lower(), m.group(2).strip()
    return None


def post_id_from_issue(issue: dict) -> str | None:
    m = POST_RE.search(issue.get("title", "")) or POST_RE.search(issue.get("body") or "")
    return m.group(0) if m else None


def handle(event: dict, owner: str) -> dict:
    comment, issue = event["comment"], event["issue"]
    actor = comment["user"]["login"]
    labels = {l["name"] for l in issue.get("labels", [])}
    out = {"approved": False, "posted": False, "post_id": None, "message": ""}
    if "approval" not in labels:
        out["message"] = "not an approval issue"
        return out
    cmd = parse_command(comment.get("body", ""))
    if not cmd:
        out["message"] = "no command"
        return out
    pid = post_id_from_issue(issue)
    out["post_id"] = pid
    if not pid:
        out["message"] = "post id not found in issue"
        return out
    if actor.lower() != owner.lower():
        out["message"] = f"@{actor} は承認権限がありません。オーナーのみ操作できます。"
        return out
    st = state.load(pid)
    verb, arg = cmd
    try:
        if verb == "approve":
            state.approve(st, actor, owner, st.get("reel_sha256", ""))
            out["approved"] = True
            out["message"] = (f"✅ 承認を記録しました（rev {st.get('revision', 0)}, sha256 {st['approved_sha256'][:12]}…）。"
                              "公開の準備を開始します。")
        elif verb == "revise":
            if not arg:
                out["message"] = "修正内容を `/revise 〜` の形で書いてください。"
                return out
            st.setdefault("revision_requests", []).append({"at": state.now(), "by": actor, "text": arg})
            state.transition(st, "revision_requested", actor, arg)
            out["message"] = ("📝 修正依頼を記録しました。Claude Code で「" + pid + " の修正依頼を反映して再レンダリングして」"
                              "と依頼してください（再生成後に新しい承認依頼が届きます）。")
        elif verb == "posted":
            state.mark_posted(st, actor, owner, arg)
            out["posted"] = True
            out["message"] = f"🎉 投稿済みとして記録しました: {st['ig']['permalink']}"
        elif verb == "reject":
            state.transition(st, "rejected", actor, arg or "(理由なし)", rejected_reason=arg)
            out["message"] = "🛑 却下を記録しました。この投稿は公開されません。"
    except state.TransitionError as e:
        out["approved"] = False
        out["message"] = f"⚠️ 操作できませんでした: {e}"
        return out
    state.save(st)
    return out


def main():
    event = json.load(open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8"))
    owner = os.environ.get("APPROVER_LOGIN") or os.environ["GITHUB_REPOSITORY_OWNER"]
    res = handle(event, owner)
    print(json.dumps(res, ensure_ascii=False))
    if res["message"] and res["message"] not in ("not an approval issue", "no command"):
        notify.issue_comment(event["issue"]["number"], res["message"])
    with open(os.environ.get("GITHUB_OUTPUT", os.devnull), "a") as f:
        f.write(f"approved={'true' if res['approved'] else 'false'}\n")
        f.write(f"posted={'true' if res['posted'] else 'false'}\n")
        f.write(f"post_id={res['post_id'] or ''}\n")


if __name__ == "__main__":
    sys.exit(main())
