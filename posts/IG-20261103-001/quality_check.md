# 品質チェック — IG-20261103-001

**判定: 合格**

| チェック | 結果 | 詳細 | ブロッキング |
|---|---|---|---|
| file exists | OK | 14040154 bytes | yes |
| video codec H.264 | OK | h264 | yes |
| pixel format yuv420p | OK | yuv420p | yes |
| resolution 1080x1920 (9:16) | OK | 1080x1920 | yes |
| frame rate 23-60 | OK | 30.00 fps | yes |
| audio AAC 48kHz | OK | aac 48000Hz ch=2 | yes |
| duration within limits | OK | 51.00s (limits 15-60) | yes |
| duration matches timeline | OK | video 51.00s / timeline 51.033s | yes |
| file size < 300MB (Instagram API) | OK | 14.0 MB | yes |
| full decode without errors | OK | clean | yes |
| no long black segments | OK | 0 segment(s) [] | yes |
| no frozen segments > 2.5s | OK | 0 segment(s) [] | no |
| loudness about -14 LUFS | OK | I=-15.2 LUFS, true peak=-1.4 dBFS | yes |
| all on-screen characters exist in the font | OK | ok | yes |
| subtitle band inside safe area | OK | center_y=1330, safe y 220..1500 | yes |
| subtitle size readable (>=56px) | OK | 64px | yes |
| caption discloses assumptions/fiction | OK | assumption/estimate/fiction claims present | yes |
| verified claims have sources | OK | ok | yes |
| TTS credit (音読さん) in caption | OK | ナレーション音声: 音読さん（ondoku3.com） | yes |
| hashtags <= 15 | OK | 13 tags | yes |
| caption+tags <= 2200 chars | OK | 341 chars | yes |
| thumbnail exists | OK | thumbnail.jpg | no |

## 人による目視確認（承認時にチェック）

- [ ] 字幕とナレーションが同期している
- [ ] 数字・固有名詞の読みが正しい（鳴門・徳島など）
- [ ] Instagram UIに字幕が隠れない
- [ ] 仮定・フィクションが誤解なく伝わる
- [ ] 徳島・地域への配慮に問題がない
