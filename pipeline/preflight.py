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


HINTS = {
    "invalid_client": "クライアントIDかクライアントシークレットが違います（貼り間違い・入れ替わり・クライアント削除）",
    "invalid_grant": "Refresh tokenが無効です（取り直しが必要。同意画面がテスト中のまま7日経過した場合もこれ）",
    "unauthorized_client": "Refresh tokenを発行したクライアントと、保存したクライアントIDが一致していません",
}


def secret_shape() -> str:
    """Format checks only; never prints values."""
    notes = []
    for name in ("GDRIVE_CLIENT_ID", "GDRIVE_CLIENT_SECRET", "GDRIVE_REFRESH_TOKEN"):
        v = os.environ.get(name, "")
        if not v:
            notes.append(f"{name}: 空")
        elif v != v.strip():
            notes.append(f"{name}: 前後に空白/改行あり（自動で除去して試行）")
    cid = os.environ.get("GDRIVE_CLIENT_ID", "").strip()
    if cid and not cid.endswith(".apps.googleusercontent.com"):
        notes.append("GDRIVE_CLIENT_ID が .apps.googleusercontent.com で終わっていない")
    sec = os.environ.get("GDRIVE_CLIENT_SECRET", "").strip()
    if sec and sec.endswith(".apps.googleusercontent.com"):
        notes.append("GDRIVE_CLIENT_SECRET にクライアントIDが入っている可能性")
    rt = os.environ.get("GDRIVE_REFRESH_TOKEN", "").strip()
    if rt and not rt.startswith("1//"):
        notes.append("GDRIVE_REFRESH_TOKEN が 1// で始まっていない（Access tokenやAuthorization codeを保存した可能性）")
    return " / ".join(notes) or "形式OK"


def drive():
    from . import drive as d
    shape = secret_shape()
    try:
        d.token()
    except RuntimeError as e:
        code = next((k for k in HINTS if k in str(e)), None)
        raise RuntimeError(f"{e} → {HINTS.get(code, '')}［形式チェック: {shape}］")
    root = json.loads((ROOT / "config/drive_folders.json").read_text())["root"]["id"]
    r = requests.get(f"{d.API}/files/{root}", headers=d._h(), params={"fields": "name,mimeType"}, timeout=30)
    r.raise_for_status()
    return f"root folder: {r.json()['name']}"


def instagram():
    from . import instagram as ig
    me = ig._req("GET", f"{ig.GRAPH}/{ig._v()}/me", params={"fields": "user_id,username,account_type",
                                                              "access_token": ig._tok()})
    lim = ig.publishing_limit()
    return f"@{me.get('username')} ({me.get('account_type')}) / user_id一致: {str(me.get('user_id')) == ig._uid()} / limit: {lim.get('data')}"


def tts_google():
    if not os.environ.get("GOOGLE_TTS_API_KEY"):
        return "任意（未設定ならOpen JTalkを使用）"
    from . import tts
    x = tts.synth_google("接続テストです。")
    return f"{len(x) / tts.SR:.1f}s audio"


def ondoku():
    if not os.environ.get("ONDOKU_TOKEN"):
        raise KeyError("ONDOKU_TOKEN")
    from . import tts
    x = tts.synth_ondoku("テスト", voice="en-US-SamuelMultilingualNeural")
    return f"Samuel（多言語）で「テスト」→ {len(x) / tts.SR:.2f}秒の音声（{tts.ondoku_chars_used}文字使用）"


def gemini():
    if not os.environ.get("GEMINI_API_KEY"):
        return "任意（未設定ならOpen JTalkを使用）"
    from . import tts
    probe = tts.gemini_probe()
    if not probe:
        raise RuntimeError("APIキーは有効ですが、TTSモデルが見つかりません")
    detail = " / ".join(f"{m}: {r}" for m, r in probe.items())
    if "OK" not in probe.values():
        hint = "（402=クレジット不足: AI Studioで課金/クレジットの設定が必要）" if any("402" in r for r in probe.values()) else ""
        raise RuntimeError(detail + hint)
    return detail


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
            check("音読さん", ondoku), check("Gemini TTS", gemini), check("Google TTS", tts_google), check("ntfy", ntfy)]
    print("| サービス | 結果 | 詳細 |\n|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} |")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write("| サービス | 結果 | 詳細 |\n|---|---|---|\n" + "".join(f"| {a} | {b} | {c} |\n" for a, b, c in rows))
