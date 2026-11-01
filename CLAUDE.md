# CLAUDE.md — 作業手順（Claude Code 用）

このリポジトリは Instagram リール「もしもAI検証」（AI仮説検証アニメーション × 徳島オチ）の制作・運用システム。
運用ドキュメントは `docs/`（Drive の instagram_post_reel にも同じものがある）。

## 「次の動画を作って」と言われたら
1. `reports/latest.md`・`reports/learnings.json`・`ideas/IDEA_DATABASE.csv` を読む（過去テーマ・分析結果）。
2. 企画候補を20案以上 `ideas/<YYYY-MM-DD>.json` に書く（10ジャンルを混ぜる。徳島が題材の回と、世界規模→徳島着地の回を両方）。
   各案を `pipeline/ideas.py` の10項目で1〜5点採点し、`decision`（上位3案比較・選定理由・没案理由・想定反応）を記入。
   `python -m pipeline.ideas ideas/<date>.json` で順位表を生成。IDEA_DATABASE.csv に追記。
3. 選んだ企画をウェブ検索で調査。公的機関・研究機関を優先。主張ごとに verified / assumption / estimate / fiction を付け、
   estimate には計算方法、verified には出典IDを必ず付ける。ページ本文を開けず検索抜粋で確認した場合はそう扱う。
4. `posts/IG-YYYYMMDD-NNN/script.json` を作成（見本: `posts/IG-20261028-001/script.json`）。
   - シーン種類は `pipeline/render/scenes.py` の SCENES から選ぶ。足りなければシーン関数を追加する。
   - 字幕の改行位置は `|`、読みが怪しい語は `tts` に読みを書く（`pyopenjtalk.g2p(text, kana=True)` で確認）。
   - ナレーションは音読さんの Masaru: `"tts": {"backend": "ondoku", "voice": "ja-JP-MasaruMultilingualNeural", "speed": 1.1}`。
     音読さんは「月」を「ガツ」と読むことがあるので、tts では「つき」などひらがなで書く。
   - キャプションに仮定・フィクションの明示と「ナレーション音声: 音読さん（ondoku3.com）」のクレジットを入れる。
   - 画面にシリーズ名や「次回も〜」の予告は入れない（BRAND_GUIDELINES.md）。
5. `python -m pipeline.schema posts/<id>/script.json` → `python -m pipeline.build <id> --preview` で試作。
   フレームを数枚書き出して目視確認（文字の重なり・はみ出し・安全領域）。尺は15〜60秒（目標30〜45秒）。
6. `python -m pytest -q tests` が通ることを確認してコミット。main に入ると produce ワークフローが本番レンダリング→Drive→承認依頼を行う。

## 投稿の仕組み（Muse）
承認後は Drive `11_Muse投稿キュー` に承認済みの版だけをコピーし、Museが投稿する（docs/MUSE_HANDOFF.md）。
`11_Muse投稿キュー` には承認フロー以外から絶対に何も置かない。投稿方式は `config/publishing.json`（muse / api）。

## 修正依頼（/revise）を反映するとき
`state/posts/<id>.json` の `revision_requests` を読み、script.json を直して上記5〜6を実施。

## 禁止事項
- 承認状態（state/）を手で `approved` / `published` に書き換えない。
- 実行していない処理・取得していない数値を、実施済み・確認済みとして書かない。
- 秘密情報をリポジトリやDriveに書かない（GitHub Secrets のみ）。
- 地域・住民を揶揄する表現、根拠のない断定をしない。著作権のある映像・音楽・キャラクターを使わない。

## コマンド
- テスト: `python -m pytest -q tests`
- 台本検証: `python -m pipeline.schema posts/<id>/script.json`
- ビルド: `python -m pipeline.build <id> [--preview] [--tts google]`
- 企画表: `python -m pipeline.ideas ideas/<date>.json`
