# instagram-ai-ops

「もしもAI検証」— AI仮説検証アニメーション × 徳島オチ の Instagram リール制作・承認・公開・分析システム。

- 運用マニュアル: [docs/00_README.md](docs/00_README.md)
- 設計・比較・費用・制約: [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)
- 必要な設定: [docs/ENV_TEMPLATE.md](docs/ENV_TEMPLATE.md)
- Claude Code 向け手順: [CLAUDE.md](CLAUDE.md)

```
pipeline/            制作エンジン（台本検証・TTS・BGM/SFX・描画・QC）と運用（承認・公開・分析）
  render/            Pillow + ffmpeg のモーショングラフィックス（シーン部品）
posts/<id>/          台本(script.json/md)・キャプション・出典・QC結果（動画本体は Drive）
state/posts/         承認・公開状態（サーバー側の正本。Actions が更新）
ideas/               企画候補と採点、企画台帳
reports/             分析レポート
.github/workflows/   produce / approval / publish / insights / token-refresh / preflight / ci
```

ローカル実行: `pip install -r requirements.txt`（ffmpeg が必要）→ `python -m pipeline.build IG-20261028-001`
