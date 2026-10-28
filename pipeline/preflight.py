"""Connection test for every external service. Prints a table; never prints secret values.

  python -m pipeline.preflight      (GitHub: Actions -> preflight -> Run workflow)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def check(name, fn):
    try:
        return name, "OK", fn()
    except KeyError as e:
        return name, "未設定", f"secret {e} がありません"
    except Exception as e:  # report and keep going
        return name, "NG", str(e)[:200]


def drive():
    from . import drive as d
    root = json.loads((ROOT / "config/drive_folders.json").read_text())["root"]["id"]
    r = requests.get(f"{d.API}/files/{root}", headers=d._h(), params={"fields": "name,mimeType"}, timeout=30)
    r.raise_for_status()
    return f"root folder: {r.json()['name']}"


def instagram():
    from . import instagram as ig
    me = ig._req("GET", f"{ig.GRAPH}/{ig._v()}/me", params={"fields": "user_id,username,account_type",
                                                              "access_token": ig._tok()})
    lim = ig.publishing_limit()
    return f"@{me.get('username')} ({me.get('account_type')}) / user_id一致: {str(me.get('user_id')) == os.environ['IG_USER_ID']} / limit: {lim.get('data')}"


def tts_google():
    if not os.environ.get("GOOGLE_TTS_API_KEY"):
        return "任意（未設定ならOpen JTalkを使用）"
    from . import tts
    x = tts.synth_google("接続テストです。")
    return f"{len(x) / tts.SR:.1f}s audio"


def github():
    r = requests.get(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}",
                     headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}, timeout=30)
    r.raise_for_status()
    return f"approver: {os.environ.get('APPROVER_LOGIN')}"


def ntfy():
    if not os.environ.get("NTFY_TOPIC"):
        return "任意（未設定）"
    from . import notify
    notify.push("接続テスト", "ntfy通知のテストです")
    return "テスト通知を送信"


if __name__ == "__main__":
    rows = [check("GitHub", github), check("Google Drive", drive), check("Instagram", instagram),
            check("Google TTS", tts_google), check("ntfy", ntfy)]
    print("| サービス | 結果 | 詳細 |\n|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} |")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("| サービス | 結果 | 詳細 |\n|---|---|---|\n" + "".join(f"| {a} | {b} | {c} |\n" for a, b, c in rows))
