"""Turn collected insights into reports/latest.md + reports/learnings.json.

Rules: missing metrics stay missing (no imputation); group comparisons are only labelled as a
trend once a group has >= MIN_N posts — before that they are shown as anecdotes.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from . import state

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
MIN_N = 5


def _rows(checkpoint: str = "72h") -> list[dict]:
    rows = []
    for p in sorted(state.STATE_DIR.glob("*.json")):
        st = json.loads(p.read_text(encoding="utf-8"))
        if st["status"] != "published":
            continue
        meta_p = ROOT / "posts" / st["post_id"] / "metadata.json"
        meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}
        ins = st.get("insights", {})
        snap = ins.get(checkpoint) or ins.get("24h")
        m = (snap or {}).get("metrics", {})
        views, reach = m.get("views"), m.get("reach")
        inter = [m.get(k) for k in ("likes", "comments", "shares", "saved")]
        er = (sum(inter) / reach) if reach and all(v is not None for v in inter) else None
        rows.append({
            "post_id": st["post_id"], "title": meta.get("title"), "published_at": st["ig"].get("published_at"),
            "checkpoint": checkpoint if ins.get(checkpoint) else ("24h" if snap else None),
            "duration": meta.get("duration_sec"), "hook": meta.get("hook"),
            "category": "/".join(meta.get("categories", [])), "ending": meta.get("tokushima_ending_type"),
            "build_seconds": meta.get("build_seconds"), "cost_usd": meta.get("cost_usd"),
            "views": views, "reach": reach, "likes": m.get("likes"), "comments": m.get("comments"),
            "shares": m.get("shares"), "saved": m.get("saved"), "avg_watch_ms": m.get("ig_reels_avg_watch_time"),
            "engagement_rate": er, "permalink": st["ig"].get("permalink"),
        })
    return rows


def _group(rows, key, metric):
    g = defaultdict(list)
    for r in rows:
        if r.get(metric) is not None:
            g[r.get(key) or "(未分類)"].append(r[metric])
    return {k: {"n": len(v), "mean": mean(v)} for k, v in g.items()}


def fmt(v, pct=False):
    if v is None:
        return "—"
    return f"{v * 100:.1f}%" if pct else (f"{v:,.0f}" if isinstance(v, (int, float)) else str(v))


def write_reports() -> Path:
    REPORTS.mkdir(exist_ok=True)
    rows = _rows()
    L = [f"# 分析レポート（{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC）", "",
         f"対象: 公開済み {len(rows)} 本。指標は72時間時点（未取得なら24時間時点）。— は未取得（推測で補完しない）。", ""]
    if len(rows) < MIN_N:
        L += [f"> ⚠️ データが{len(rows)}本しかないため、以下は傾向ではなく個別の記録です。{MIN_N}本以上で比較を有効にします。", ""]
    L += ["| 投稿 | 再生 | リーチ | いいね | コメント | シェア | 保存 | 平均視聴(秒) | ER | 尺 |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        aw = r["avg_watch_ms"] / 1000 if r["avg_watch_ms"] is not None else None
        L.append(f"| [{r['post_id']}]({r['permalink']}) {r['title']} | {fmt(r['views'])} | {fmt(r['reach'])} | {fmt(r['likes'])} | "
                 f"{fmt(r['comments'])} | {fmt(r['shares'])} | {fmt(r['saved'])} | {fmt(aw and round(aw, 1))} | "
                 f"{fmt(r['engagement_rate'], True)} | {fmt(r['duration'])}s |")
    learnings = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n_posts": len(rows),
                 "min_n_for_trend": MIN_N, "by_ending": _group(rows, "ending", "engagement_rate"),
                 "by_category": _group(rows, "category", "engagement_rate"), "by_hook_views": _group(rows, "hook", "views")}
    for title, key in (("徳島オチのタイプ別 ER", "by_ending"), ("分類別 ER", "by_category")):
        L += ["", f"## {title}", ""]
        for k, v in learnings[key].items():
            tag = "" if v["n"] >= MIN_N else "（参考値・サンプル不足）"
            L.append(f"- {k}: 平均 {v['mean'] * 100:.1f}%（n={v['n']}）{tag}")
    L += ["", "## 次回企画への反映", "",
          "- 企画スコアリング時に `reports/learnings.json` を参照する（n が足りないグループは重みを変えない）",
          "- 平均視聴時間が尺の50%未満の投稿は、冒頭3秒と中盤の展開を見直す候補にする",
          "- コメント数の多い徳島オチのタイプを次回の候補に1つ以上含める"]
    out = REPORTS / "latest.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    (REPORTS / "learnings.json").write_text(json.dumps(learnings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        from . import drive
        drive.upload(out, drive.FOLDERS["08_reports"], f"report_{datetime.now(timezone.utc):%Y%m%d}.md")
    except Exception as e:  # Drive credentials may be absent locally
        print("report upload skipped:", e)
    return out


if __name__ == "__main__":
    print(write_reports())
