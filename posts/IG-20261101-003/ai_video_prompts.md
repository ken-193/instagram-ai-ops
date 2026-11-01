# もしも阿波踊りが東京を襲撃したら？ — AI動画生成プロンプト

このリールはコード生成のアニメーションで作っています。実写風の映像に差し替えたい場合は、各シーンのプロンプトを動画生成サービスに渡し、下の秒数に合わせて編集します（ナレーション・字幕・BGMは out/narration.wav, out/subtitles.srt, out/bgm_sfx.wav をそのまま使えます）。

共通: vertical 9:16, 1080x1920, photorealistic, cinematic, consistent costumes (Awa-odori: yukata, folded straw amigasa hats, happi coats, paper lanterns), no on-screen text, no logos, no real advertisements.

## s1（0.0〜3.6秒 / 3.6秒）

- 映像: 渋谷の大通りを見下ろす街頭カメラ。地面が細かく揺れ、通りの奥から阿波踊りの大群が迫ってくる。タイトルは0秒目から中央に表示。
- カメラ: ゆっくり後退しながら揺れる（報道カメラ風）
- ナレーション: 緊急事態です。

```
Photorealistic cinematic vertical 9:16 shot, Shibuya scramble crossing in Tokyo on an ordinary afternoon, pedestrians stop and turn, the ground trembles slightly, far down the avenue a huge crowd in Awa-odori costumes (yukata, folded straw amigasa hats, happi coats, paper lanterns) advances toward camera, slow push-in, handheld news-camera feel, overcast light, no text
```

## s2（3.6〜11.1秒 / 7.5秒）

- 映像: 真上からの空撮。碁盤の目の街を、編み笠と浴衣の踊り手の波が下から上へ埋めていく。
- カメラ: 上昇しながら少し回転（ドローン）
- ナレーション: 東京に、謎の大群が出現。 その正体は…徳島の、阿波踊り。

```
Photorealistic aerial drone shot, vertical 9:16, a Tokyo city grid seen from above, thousands of Awa-odori dancers in indigo and red yukata with straw hats flow through every street like a wave, camera slowly rising and rotating, late afternoon sun, long building shadows, no text
```

## s3（11.1〜17.5秒 / 6.4秒）

- 映像: 前半：ビルと大型ビジョンを見上げるローアングル、手前を踊り手が横切る。後半：交差点の真上からの俯瞰。踊り手が中心から広がり交差点を埋める。
- カメラ: 見上げ → ホワイトフラッシュ → 真上の俯瞰（ゆっくり回転）
- ナレーション: 渋谷。 スクランブル交差点が、踊りで埋め尽くされました。

```
Photorealistic vertical 9:16, low angle from the street looking up at Shibuya buildings and giant video screens while Awa-odori dancers pass close to camera raising both hands, same-side hand and foot stepping forward together; then a whip to a top-down drone shot of the Shibuya scramble crossing completely filled with dancers, no text
```

## s4（17.5〜23.5秒 / 6.0秒）

- 映像: 夕暮れの高層ビルの谷間を前進するカメラ。通りは奥まで踊り手で埋まり、太鼓に合わせて衝撃波の輪が広がる。
- カメラ: ドリーイン（前進）しながら少し上昇
- ナレーション: 新宿。 東京の主要エリアが、次々と踊りに包まれていきます。

```
Photorealistic vertical 9:16, Shinjuku skyscraper canyon at dusk, camera dollies forward at second-floor height above an avenue packed with Awa-odori dancers, taiko drums and shinobue flutes, lanterns glowing, glass towers reflecting orange sky, epic scale, no text
```

## s5（23.5〜30.3秒 / 6.8秒）

- 映像: 夜の東京タワー。提灯を持った踊り手の輪が外側へ何重にも増え、回りながらタワーを囲む。
- カメラ: ドローンで周回しながら上昇（背景の街が流れる）
- ナレーション: そして、東京タワー。 提灯の光が、夜の東京を照らします。

```
Photorealistic vertical 9:16 night drone orbit around Tokyo Tower, tens of thousands of dancers with glowing paper lanterns form huge rings around the tower, warm lantern light on the streets, cinematic climax, no text
```

## s6（30.3〜37.7秒 / 7.4秒）

- 映像: 提灯が吊られた夕方の通り。スーツの会社員、観光客、学生が「？」の顔で見ている → 一人が先に踊り出し、続いて全員がカバンを置いて笑顔で踊り出す。
- カメラ: ゆっくり前進するミディアムショット
- ナレーション: しかし、異変はここからでした。 踊りを見ていた人々が、次々と踊り始めたのです。

```
Photorealistic vertical 9:16, festival-lit Tokyo street in the evening, a salaryman in a suit with a briefcase, tourists and locals watch the Awa-odori procession with confused faces, then one by one they drop their bags, raise their hands and start dancing with big smiles, medium shot, natural faces and hands, no text
```

## s7（37.7〜43.5秒 / 5.8秒）

- 映像: 東京都の地図。新宿から踊り手の点が同心円状に広がり、多摩の山まで埋まる。経過時間と踊っている人の割合が100％に。
- カメラ: 新宿の寄りから東京都全体へズームアウト
- ナレーション: わずか30分で、東京は、巨大な阿波踊り会場に。

```
Photorealistic vertical 9:16, very high aerial shot of all of Tokyo at blue hour, every street, park and plaza filled with dancers and lanterns, the whole city glowing like one giant festival ground, slow pull back, no text
```

## s8（43.5〜48.3秒 / 4.8秒）

- 映像: 夕暮れの東京（遠くに東京タワー）と、手前で笑顔で踊る人々。中央に大きな看板テロップがドンと出て、少し間を置いて『（旧）東京』の札が付く。
- カメラ: 固定（間を取る）
- ナレーション: 東京、徳島支部になりました。

```
Photorealistic vertical 9:16, Tokyo skyline at dusk with Tokyo Tower in the distance, happy Awa-odori dancers fill the foreground, calm wide shot holding still, empty area in the centre for a title card, no text
```
