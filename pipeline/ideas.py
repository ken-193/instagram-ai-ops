"""Idea scoring + de-duplication.

  python -m pipeline.ideas ideas/2026-10-28.json   -> prints ranked table, writes <file>.md

Scores are 1-5 judgements per criterion; the weighted total is a way to compare candidates,
NOT a prediction of views.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDEA_DB = ROOT / "ideas" / "IDEA_DATABASE.csv"

WEIGHTS = {  # sums to 1.0
    "hook": 0.15,            # 冒頭1〜3秒の引き
    "clarity": 0.10,         # 仮説の理解しやすさ
    "surprise": 0.10,        # 展開の意外性
    "scale": 0.10,           # スケールアップの面白さ
    "animation": 0.10,       # アニメーションで表現する価値
    "tokushima": 0.15,       # 徳島オチの自然さと強さ
    "engagement": 0.10,      # コメント・共有を生む可能性
    "credibility": 0.10,     # 科学的・事実的な信頼性
    "feasibility": 0.05,     # 制作コストと映像化の容易さ（高いほど容易）
    "originality": 0.05,     # 類似コンテンツとの差別化
}
LABELS = {"hook": "引き", "clarity": "理解", "surprise": "意外", "scale": "拡大", "animation": "映像",
          "tokushima": "徳島", "engagement": "反応", "credibility": "信頼", "feasibility": "制作", "originality": "独自"}


def total(scores: dict) -> float:
    return round(sum(WEIGHTS[k] * scores[k] for k in WEIGHTS) / 5 * 100, 1)


def bigrams(s: str) -> set[str]:
    s = "".join(ch for ch in s if ch.isalnum())
    return {s[i:i + 2] for i in range(len(s) - 1)}


def similarity(a: str, b: str) -> float:
    A, B = bigrams(a), bigrams(b)
    return len(A & B) / len(A | B) if A and B else 0.0


def past_titles() -> list[str]:
    if not IDEA_DB.exists():
        return []
    with open(IDEA_DB, encoding="utf-8-sig") as f:
        return [r["仮説"] for r in csv.DictReader(f) if r.get("制作状況") not in ("候補", "", None)]


def rank(ideas: list[dict]) -> list[dict]:
    past = past_titles()
    for i in ideas:
        missing = set(WEIGHTS) - set(i["scores"])
        if missing:
            raise ValueError(f"{i['title']}: missing scores {missing}")
        i["total"] = total(i["scores"])
        sim = max((similarity(i["hypothesis"], p) for p in past), default=0.0)
        i["similar_to_past"] = round(sim, 2)
        if sim >= 0.5:
            i["total"] = round(i["total"] - 15, 1)  # strong penalty for near-repeats
    return sorted(ideas, key=lambda x: x["total"], reverse=True)


def to_markdown(ranked: list[dict]) -> str:
    head = "| # | 仮説 | ジャンル | " + " | ".join(LABELS[k] for k in WEIGHTS) + " | 総合 | 既存類似 |"
    L = ["# 企画候補と評価", "", "重み: " + "、".join(f"{LABELS[k]} {int(w * 100)}%" for k, w in WEIGHTS.items()), "",
         "> 総合スコアは候補を比較するための仮説評価です。再生数や成功率の予測ではありません。", "",
         head, "|" + "---|" * (len(WEIGHTS) + 5)]
    for n, i in enumerate(ranked, 1):
        L.append(f"| {n} | {i['hypothesis']} | {i['genre']} | " + " | ".join(str(i['scores'][k]) for k in WEIGHTS)
                 + f" | **{i['total']}** | {i['similar_to_past']} |")
    return "\n".join(L) + "\n"


def main(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    ranked = rank(data["ideas"])
    md = to_markdown(ranked)
    if data.get("decision"):
        d = data["decision"]
        md += "\n## 上位3案の比較と選定\n\n" + d["comparison"] + "\n\n### 選定\n\n" + d["selected"] + "\n\n### 選定理由\n\n" + \
              d["reason"] + "\n\n### 没案の理由\n\n" + "\n".join(f"- {k}: {v}" for k, v in d["rejected"].items()) + \
              "\n\n### 想定する視聴者の反応\n\n" + "\n".join(f"- {x}" for x in d["expected_reactions"]) + "\n"
    Path(path).with_suffix(".md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main(sys.argv[1])
