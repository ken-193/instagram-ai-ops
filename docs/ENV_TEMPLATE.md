# ENV_TEMPLATE — 必要な設定（秘密情報は書かない）

このファイルには **名前と用途だけ** を記載します。値（APIキー・トークン・パスワード）は GitHub Secrets にのみ保存してください。

設定場所（iPhoneのSafariで可・GitHubアプリでは設定不可）:
`github.com/ken-193/instagram-ai-ops` → Settings → Secrets and variables → Actions

## Secrets（秘密情報）

| 名前 | 必須 | 用途 | 取得先 |
|---|---|---|---|
| `GDRIVE_CLIENT_ID` | 必須 | Drive へのアップロード（OAuthクライアント） | Google Cloud Console |
| `GDRIVE_CLIENT_SECRET` | 必須 | 同上 | Google Cloud Console |
| `GDRIVE_REFRESH_TOKEN` | 必須 | あなたのDriveに書き込むための更新トークン（scope: `https://www.googleapis.com/auth/drive`） | OAuth 2.0 Playground |
| `IG_USER_ID` | 任意（Muse投稿のため現在不要。API投稿・インサイト取得に切り替える場合のみ） | InstagramのユーザーID | Meta for Developers（アプリのInstagram設定画面） |
| `IG_ACCESS_TOKEN` | 任意（同上） | 長期アクセストークン（60日） | 同上 |
| `ONDOKU_TOKEN` | 必須（ナレーション） | 音読さんのアクセストークン。ナレーション音声の生成 | 音読さん（https://ondoku3.com/ja/users/setting/）※無料登録 |
| `GEMINI_API_KEY` | 任意 | Geminiの音声合成（男性ナレーション）。未設定なら無料のOpen JTalk | Google AI Studio（https://aistudio.google.com/apikey） |
| `GOOGLE_TTS_API_KEY` | 任意 | 自然な日本語ナレーション（Chirp 3 HD）。未設定なら無料のOpen JTalk | Google Cloud Console（Text-to-Speech APIを有効化） |
| `NTFY_TOPIC` | 任意 | ntfyアプリへのプッシュ通知。推測されにくいランダムな文字列にする | 自分で決める（ntfyアプリで同じトピックを購読） |
| `SECRETS_PAT` | 任意 | Instagramトークンの自動更新でSecretを書き換えるため | GitHub → Settings → Developer settings → Fine-grained token（このリポジトリのみ、Secrets: Read and write） |

## Variables（秘密ではない設定）

| 名前 | 既定値 | 用途 |
|---|---|---|
| `APPROVER_LOGIN` | リポジトリのオーナー（ken-193） | 承認コマンドを受け付けるGitHubユーザー |
| `GEMINI_TTS_MODEL` | （空＝自動選択） | 使うGemini TTSモデル名。廃止された場合はAPIが提供するTTSモデルを自動で選ぶ |
| `IG_API_VERSION` | `v23.0` | Instagram APIのバージョン。Metaの変更履歴を見て更新 |

## 設定手順

### A. Google Drive（必須・約15分）
画面名は変更されることがあります。
1. Google Cloud Console で新規プロジェクトを作成し、**Google Drive API** を有効化。
2. 「OAuth 同意画面」: 外部 → アプリ名を入力 → 自分のGmailをテストユーザーに追加 → 最後に **「アプリを公開（本番）」** に切り替える。
   - テスト状態のままだと更新トークンが7日で失効します。未審査アプリの警告画面が出ますが、自分だけが使う用途なら続行できます。
3. 「認証情報」→ OAuth クライアントID → 種類「ウェブアプリケーション」→ 承認済みリダイレクトURIに `https://developers.google.com/oauthplayground` を追加 → クライアントID/シークレットを控える。
4. `https://developers.google.com/oauthplayground` → 右上の歯車 → 「Use your own OAuth credentials」に3.の値 → 左の入力欄に `https://www.googleapis.com/auth/drive` → Authorize → Exchange authorization code for tokens → **Refresh token** を控える。
5. 3つの値を Secrets に保存。

### B. Instagram API（任意・Museを使う間は不要）
1. Instagramアプリ → 設定 → アカウントの種類 → **プロアカウント（クリエイターまたはビジネス）** に切り替え。
2. Meta for Developers でアプリを作成し、「Instagram」製品の **API setup with Instagram login** を追加。
3. 自分のInstagramアカウントを追加し、権限 `instagram_business_basic`, `instagram_business_content_publish`, `instagram_business_manage_insights` でトークンを生成。
4. 表示される **ユーザーID** と **アクセストークン（長期）** を Secrets に保存。
   - 自分のアカウントだけで使う場合、アプリは開発モードのままで利用できる想定です（初回の接続テストで確認します）。

### C. 音読さん（ナレーション）
1. https://ondoku3.com で無料登録してログイン。
2. https://ondoku3.com/ja/users/setting/ を開き、アクセストークンをコピー。
3. `ONDOKU_TOKEN` として Secrets に保存。
4. 無料プランは月ごとの文字数に上限あり（1本あたり約400〜500文字）。上限に達すると制作がエラーで止まります（案内音声が混ざることはありません）。
5. 利用規約・クレジット表記の条件はプランにより異なるため、音読さんの公式ページで確認してください。キャプションには「ナレーション音声: 音読さん（ondoku3.com）」を入れます。

### C2. Gemini 音声（任意・現在は未使用）
1. https://aistudio.google.com/apikey を開き、オーナーの Google アカウントでログイン → 「APIキーを作成」。
2. 既存のGoogle Cloudプロジェクト（`reel-ops`）を選ぶか、新規作成でOK。
3. 表示されたキーを `GEMINI_API_KEY` として Secrets に保存。
4. 無料枠の有無・料金はモデルにより変わります。課金を有効にしない限り請求は発生しません（無料枠を超えるとエラーになります）。
   無料枠では入力内容がGoogleの品質改善に使われる場合があります（台本のみで個人情報は含みません）。

### D. 任意
- ntfy: App Storeで「ntfy」をインストール → ランダムなトピック名を購読 → 同じ文字列を `NTFY_TOPIC` に保存。
- 自然な音声: Google Cloud Console で Text-to-Speech API を有効化 → APIキー作成（Text-to-Speech APIのみに制限）→ `GOOGLE_TTS_API_KEY`。台本の `tts.backend` を `google` に。

## 接続テスト方法
GitHubアプリ → リポジトリ → Actions → **preflight** → Run workflow。
結果画面にサービスごとの OK / 未設定 / NG が表示されます（秘密情報の値は表示されません）。
