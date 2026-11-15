"""Weekly competitor snapshot via Instagram Business Discovery, appended to the owner's Google Sheet.

  python -m pipeline.competitors [--dry-run]

Business Discovery is only in the Instagram API *with Facebook Login* (graph.facebook.com): the owner's
Instagram professional account must be linked to a Facebook Page, and the token needs instagram_basic +
pages_show_list (+ pages_read_engagement / business_management depending on the app setup).
Env: IG_FB_USER_ID (the owner's Instagram business account id on graph.facebook.com),
     IG_FB_ACCESS_TOKEN (long-lived user token), IG_API_VERSION (default v23.0),
     GDRIVE_* (the same Google OAuth token as Drive; the drive scope also allows the Sheets API).

What it can see for another account: followers, number of posts, and for recent posts the type, date,
like count (unless the owner hid likes), comment count and caption. Views/reach of other people's reels
are NOT available through any official API, so they are not collected.

STATUS: written against Meta's documented Business Discovery fields; not yet exercised against the live API
(the development sandbox cannot reach graph.facebook.com). Watch the first run.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "competitors.json"
GRAPH = "https://graph.facebook.com"
SHEETS = "https://sheets.googleapis.com/v4/spreadsheets"
JST = timezone(timedelta(hours=9))
HEADER = ["取得日", "アカウント", "ラベル", "フォロワー", "投稿数", "直近の投稿数（集計対象）", "うちリール",
          "平均いいね", "平均コメント", "中央値いいね", "最多いいねの投稿", "最多いいね数", "最新投稿日", "状態"]


def _env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise KeyError(name)
    return v


def discover(username: str, n: int) -> dict:
    fields = (f"business_discovery.username({username})"
              f"{{username,name,followers_count,media_count,"
              f"media.limit({n}){{timestamp,media_type,media_product_type,like_count,comments_count,permalink,caption}}}}")
    r = requests.get(f"{GRAPH}/{os.environ.get('IG_API_VERSION', 'v23.0')}/{_env('IG_FB_USER_ID')}",
                     params={"fields": fields, "access_token": _env("IG_FB_ACCESS_TOKEN")}, timeout=60)
    data = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in data:
        msg = (data.get("error") or {}).get("message", r.text[:300])
        raise RuntimeError(f"{username}: {r.status_code} {msg}")
    return data["business_discovery"]


def summarize(bd: dict, label: str, day: str) -> list:
    posts = (bd.get("media") or {}).get("data", [])
    likes = [p["like_count"] for p in posts if isinstance(p.get("like_count"), int)]
    comments = [p["comments_count"] for p in posts if isinstance(p.get("comments_count"), int)]
    reels = sum(1 for p in posts if p.get("media_product_type") == "REELS")
    top = max((p for p in posts if isinstance(p.get("like_count"), int)), key=lambda p: p["like_count"], default=None)
    latest = max((p["timestamp"] for p in posts if p.get("timestamp")), default="")
    return [day, "@" + bd.get("username", ""), label, bd.get("followers_count", ""), bd.get("media_count", ""),
            len(posts), reels,
            round(statistics.mean(likes)) if likes else "", round(statistics.mean(comments)) if comments else "",
            statistics.median(likes) if likes else "", top.get("permalink", "") if top else "",
            top["like_count"] if top else "", latest[:10], "OK" if likes else "OK（いいね数は非公開）"]


def _google_token() -> str:
    from .drive import token
    return token()


def ensure_sheet(sid: str, title: str) -> None:
    h = {"Authorization": f"Bearer {_google_token()}"}
    meta = requests.get(f"{SHEETS}/{sid}", headers=h, params={"fields": "sheets.properties.title"}, timeout=30)
    meta.raise_for_status()
    if title in [s["properties"]["title"] for s in meta.json().get("sheets", [])]:
        return
    requests.post(f"{SHEETS}/{sid}:batchUpdate", headers=h, timeout=30,
                  json={"requests": [{"addSheet": {"properties": {"title": title,
                                                                  "gridProperties": {"frozenRowCount": 1}}}}]}
                  ).raise_for_status()
    append(sid, title, [HEADER])


def append(sid: str, title: str, rows: list) -> None:
    r = requests.post(f"{SHEETS}/{sid}/values/'{title}'!A1:append", timeout=30,
                      headers={"Authorization": f"Bearer {_google_token()}"},
                      params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, json={"values": rows})
    r.raise_for_status()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print rows instead of writing the sheet")
    a = ap.parse_args(argv)
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    day = datetime.now(JST).strftime("%Y-%m-%d")
    rows, raw, errors = [], {}, []
    for acc in cfg["accounts"]:
        try:
            bd = discover(acc["username"], cfg.get("recent_posts", 12))
            raw[acc["username"]] = bd
            rows.append(summarize(bd, acc.get("label", ""), day))
        except Exception as e:  # one private/non-business account must not stop the others
            errors.append(str(e))
            rows.append([day, "@" + acc["username"], acc.get("label", "")] + [""] * 10 + [f"取得できず: {e}"[:200]])
    out = ROOT / "reports" / "competitors"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{day}.json").write_text(json.dumps({"date": day, "accounts": raw, "errors": errors},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    if a.dry_run:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    ensure_sheet(cfg["spreadsheet_id"], cfg["sheet"])
    append(cfg["spreadsheet_id"], cfg["sheet"], rows)
    print(f"{len(rows)} rows appended; {len(errors)} errors")
    for e in errors:
        print("  ", e)


if __name__ == "__main__":
    main()
