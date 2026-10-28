"""Notifications to the owner's iPhone.

Primary: GitHub issues/comments (GitHub iOS app pushes these to the owner).
Optional: ntfy (free iOS app) when NTFY_TOPIC is set — secret topic name, keep it unguessable.
"""
from __future__ import annotations

import os

import requests

API = "https://api.github.com"


def _gh(method: str, url: str, **kw):
    token = os.environ["GITHUB_TOKEN"]
    r = requests.request(method, API + url, headers={"Authorization": f"Bearer {token}",
                                                      "Accept": "application/vnd.github+json"}, timeout=30, **kw)
    r.raise_for_status()
    return r.json() if r.content else {}


def repo() -> str:
    return os.environ["GITHUB_REPOSITORY"]


def create_issue(title: str, body: str, labels: list[str], assignee: str | None = None) -> int:
    data = {"title": title, "body": body, "labels": labels}
    if assignee:
        data["assignees"] = [assignee]
    return _gh("POST", f"/repos/{repo()}/issues", json=data)["number"]


def issue_comment(number: int, body: str) -> None:
    _gh("POST", f"/repos/{repo()}/issues/{number}/comments", json={"body": body})


def close_issue(number: int, reason: str = "completed") -> None:
    _gh("PATCH", f"/repos/{repo()}/issues/{number}", json={"state": "closed", "state_reason": reason})


def push(title: str, message: str, url: str | None = None, priority: str = "default") -> None:
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return
    headers = {"Title": title.encode("utf-8"), "Priority": priority}
    if url:
        headers["Click"] = url
    try:
        requests.post(f"https://ntfy.sh/{topic}", data=message.encode("utf-8"), headers=headers, timeout=15)
    except requests.RequestException as e:  # notification failure must not break the pipeline
        print("ntfy failed:", e)


def error(context: str, detail: str) -> None:
    """Called from workflow `if: failure()` steps."""
    run_url = f"https://github.com/{repo()}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    body = f"### ⚠️ エラー: {context}\n\n```\n{detail[-3000:]}\n```\n\n実行ログ: {run_url}"
    try:
        create_issue(f"[エラー] {context}", body, ["error"], os.environ.get("APPROVER_LOGIN"))
    finally:
        push(f"エラー: {context}", detail[-300:], run_url, priority="high")


if __name__ == "__main__":
    import sys

    error(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "詳細は実行ログを確認してください")
