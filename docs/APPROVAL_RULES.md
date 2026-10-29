# APPROVAL_RULES — 承認・修正・却下のルール

## 大原則
**オーナーが明示的に承認していない動画は、いかなる経路でも公開しない。**
承認状態は通知や画面ではなく、サーバー側の状態ファイル `state/posts/<投稿ID>.json`（GitHubに記録）で判定します。

## 承認依頼が届く条件
- 自動品質チェックにすべて合格した版だけが `06_承認待ち/<投稿ID>/` に保存され、GitHub Issue（ラベル `approval`）で通知されます。
- 依頼には動画リンク、キャプション、版番号（rev）、動画ファイルの sha256（先頭16桁）が記載されます。

## 操作（Issueへの返信。オーナーのみ有効）

| コマンド | 結果 |
|---|---|
| `/approve` | 現在レビュー中の版を承認 → `11_Muse投稿キュー` へ受け渡し（Museが投稿） |
| `/revise 修正内容` | 修正依頼として記録 → Claude Codeで反映・再生成 → 新しい版の承認依頼が届く |
| `/reject 理由` | 却下（終了状態）。この投稿は公開されません |
| `/posted URL` | Museで投稿したあとに記録。キューのファイルを投稿済みフォルダへ移動しIssueを閉じる |

承認時の目視チェック（quality_check.md 末尾）: 字幕とナレーションの同期／数字・地名の読み／字幕がUIに隠れない／仮定・フィクションが誤解なく伝わる／地域への配慮。

## 誤操作・二重処理の防止
| 起こりうること | 防止策 |
|---|---|
| オーナー以外が `/approve` | 無視して記録しない（`APPROVER_LOGIN` と照合） |
| `/approve` を2回送信・通知の二重タップ | 2回目は状態が `approved` 以降のため拒否 |
| 承認後に動画が差し替わる | 承認は sha256 に紐づく。公開時にDriveから取得したファイルのsha256が一致しなければ公開しない |
| 修正版の制作中に古い版を承認 | 状態が `pending_approval` でないため拒否 |
| 公開処理の再実行 | 状態が `published` なら何もしない。`publishing` / `publish_unknown` なら照合のみ（新規投稿しない） |
| 同時実行 | GitHub Actions の concurrency で投稿ごとに直列化 |

## 状態遷移
```
drafted → rendered → pending_approval ─┬→ approved → handed_off（Museキュー）→ published（/posted）
                         ↑             ├→ revision_requested → (再生成) → rendered
                         └─(新しい版)───┘└→ rejected（終了）
（Instagram API モード時のみ）approved → publishing → published / publish_unknown / publish_failed
```

## 承認履歴の記録
- すべての遷移が `history`（日時・前後の状態・操作者・メモ）に追記され、gitのコミットとしても残ります。
- 承認時は `approved_by`, `approved_at`, `approved_sha256`, `approved_revision` を記録。
- キューへの受け渡し時は `muse.files`（コピーしたファイルID）と日時を記録。
- `/posted` 後は `ig.permalink`, `ig.published_at` を記録し、Driveのフォルダとキューのファイルを `07_投稿済み` へ移動します。
- 却下は `rejected_reason` を記録します。
