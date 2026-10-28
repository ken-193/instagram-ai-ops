"""Generate the human-readable per-post files from script.json + timeline."""
from __future__ import annotations

from pathlib import Path

from .render.engine import strip_hints
from .schema import CATEGORIES

STATUS_JA = {"verified": "確認済みの事実", "assumption": "仮定", "estimate": "推定・概算", "fiction": "フィクション"}


def fmt_t(s: float) -> str:
    return f"{int(s // 60)}:{s % 60:05.2f}"


def script_md(script: dict, timeline: dict | None) -> str:
    tl = {s["id"]: s for s in (timeline or {}).get("scenes", [])}
    L = [f"# {script['title']}", "",
         f"- 投稿ID: `{script['post_id']}`",
         f"- 動画の分類: {' / '.join(CATEGORIES[c] for c in script['categories'])}",
         f"- ジャンル: {script['genre']}",
         f"- 想定視聴者: {script['target_audience']}",
         f"- 尺: {timeline['total']:.1f} 秒" if timeline else "- 尺: (未レンダリング)",
         "", "## 企画概要", script["summary"], "", "## 仮説の前提", script["premise"], "",
         "## 冒頭フック", f"> {script['hook']}", "",
         "## 徳島オチ", f"- タイプ: {script['tokushima_ending']['type']}", f"- 説明: {script['tokushima_ending']['description']}", "",
         "## BGMの方向性", f"{script['bgm'].get('mood')}（{script['bgm'].get('bpm')} BPM, 手続き生成・権利問題なし）", "",
         "## ナレーション全文", ""]
    for sc in script["scenes"]:
        for ln in sc["narration"]:
            L.append(strip_hints(ln["text"]))
    L += ["", "## シーン構成", ""]
    for sc in script["scenes"]:
        m = tl.get(sc["id"])
        when = f"{fmt_t(m['start'])} – {fmt_t(m['end'])}" if m else "未計算"
        L += [f"### {sc['id']}  {when}  `{sc['type']}`", "",
              "| 項目 | 内容 |", "|---|---|",
              f"| ナレーション | {' '.join(strip_hints(l['text']) for l in sc['narration'])} |",
              f"| 画面内テキスト | {' / '.join(sc['on_screen_text'])} |",
              f"| アニメーション | {sc['animation']} |",
              f"| カメラワーク | {sc['camera']} |",
              f"| 効果音 | {', '.join(sc['sfx']) or '-'} |",
              f"| 動画生成プロンプト | {sc['video_prompt']} |", ""]
        if m:
            L += ["字幕タイミング:", ""] + [f"- {fmt_t(m['start'] + l['start'])} – {fmt_t(m['start'] + l['end'])} {strip_hints(l['text'])}"
                                          for l in m["lines"]] + [""]
    L += ["## 事実確認が必要な項目", "", "| 主張 | 区分 | 根拠・計算方法 |", "|---|---|---|"]
    for fc in script["fact_checks"]:
        basis = fc.get("method") or fc.get("note") or ""
        if fc.get("source_ids"):
            basis = (basis + " 出典: " + ", ".join(fc["source_ids"])).strip()
        L.append(f"| {fc['claim']} | {STATUS_JA[fc['status']]} | {basis} |")
    L += ["", "## 出典", ""] + [f"- [{s['id']}] {s['title']} — {s['url']}" for s in script["sources"]]
    L += ["", "## キャプション", "", "```", script["caption"], "", " ".join(script["hashtags"]), "```", "",
          "## 固定コメント案", script["pinned_comment"], "", "## サムネイル文字", script["thumbnail_text"], "",
          "## 制作上の注意点", ""] + [f"- {n}" for n in script["production_notes"]]
    return "\n".join(L) + "\n"


def sources_md(script: dict) -> str:
    L = [f"# 出典・事実確認 — {script['post_id']}", "",
         "区分: 確認済みの事実 / 仮定 / 推定・概算 / フィクション", "",
         "> 確認方法の注記: 制作環境のネットワーク制限により、出典ページ本文の直接取得ができないものは"
         "検索エンジン経由の抜粋で内容を確認しています。公開前に主要な出典リンクを開いて確認してください。", "",
         "## 主張と根拠の対応", ""]
    for fc in script["fact_checks"]:
        L.append(f"- **[{STATUS_JA[fc['status']]}]** {fc['claim']}")
        if fc.get("method"):
            L.append(f"  - 計算方法・前提: {fc['method']}")
        if fc.get("note"):
            L.append(f"  - 注記: {fc['note']}")
        for sid in fc.get("source_ids", []):
            s = next(x for x in script["sources"] if x["id"] == sid)
            L.append(f"  - 出典: {s['title']} <{s['url']}>")
    L += ["", "## 出典一覧", "", "| ID | タイトル | URL | 参照日 | 用途 |", "|---|---|---|---|---|"]
    L += [f"| {s['id']} | {s['title']} | {s['url']} | {s['accessed']} | {s['used_for']} |" for s in script["sources"]]
    L += ["", "## 素材のライセンス", "",
          "- 地図: Natural Earth（パブリックドメイン） https://www.naturalearthdata.com/",
          "- フォント: Dela Gothic One / Noto Sans JP（SIL Open Font License 1.1）",
          "- BGM・効果音: コードで手続き生成（第三者素材なし）"]
    if script.get("tts", {}).get("backend", "openjtalk") == "openjtalk":
        L.append("- ナレーション: Open JTalk + HTS voice \"Mei\"（CC BY 3.0, Nagoya Institute of Technology） → キャプションにクレジット記載")
    return "\n".join(L) + "\n"


def qc_md(report: dict, post_id: str) -> str:
    L = [f"# 品質チェック — {post_id}", "", f"**判定: {'合格' if report['passed'] else '不合格'}**", "",
         "| チェック | 結果 | 詳細 | ブロッキング |", "|---|---|---|---|"]
    for c in report["checks"]:
        L.append(f"| {c['check']} | {'OK' if c['ok'] else 'NG'} | {str(c['detail']).replace('|', '/')} | {'yes' if c['blocking'] else 'no'} |")
    L += ["", "## 人による目視確認（承認時にチェック）", "",
          "- [ ] 字幕とナレーションが同期している", "- [ ] 数字・固有名詞の読みが正しい（鳴門・徳島など）",
          "- [ ] Instagram UIに字幕が隠れない", "- [ ] 仮定・フィクションが誤解なく伝わる", "- [ ] 徳島・地域への配慮に問題がない"]
    return "\n".join(L) + "\n"


def write_post_docs(post_dir: Path, script: dict, timeline: dict, report: dict):
    (post_dir / "script.md").write_text(script_md(script, timeline), encoding="utf-8")
    (post_dir / "caption.txt").write_text(script["caption"] + "\n\n" + " ".join(script["hashtags"]) + "\n", encoding="utf-8")
    (post_dir / "sources.md").write_text(sources_md(script), encoding="utf-8")
    (post_dir / "quality_check.md").write_text(qc_md(report, script["post_id"]), encoding="utf-8")
