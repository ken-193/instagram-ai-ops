# 出典・事実確認 — IG-20261028-001

区分: 確認済みの事実 / 仮定 / 推定・概算 / フィクション

> 確認方法の注記: 制作環境のネットワーク制限により、出典ページ本文の直接取得ができないものは検索エンジン経由の抜粋で内容を確認しています。公開前に主要な出典リンクを開いて確認してください。

## 主張と根拠の対応

- **[確認済みの事実]** 月までの平均距離は約384,400km
  - 出典: NASA Science - Moon Facts <https://science.nasa.gov/moon/facts/>
  - 出典: NASA JPL CNEOS - LD (Lunar Distance) <https://cneos.jpl.nasa.gov/glossary/LD.html>
- **[確認済みの事実]** 月が起こす潮汐力は距離の3乗に反比例する（距離が半分なら8倍）
  - 注記: 月による地球の潮汐の起潮力についての関係。太陽による潮汐は変わらないため、潮汐全体がちょうど8倍になるわけではない。
  - 出典: Universe (Freedman et al.) Box 10-1 Calculating Tidal Forces <https://digfir-published.macmillanusa.com/universe10e/asset/boxes/10_1.html>
- **[推定・概算]** 見た目の大きさ(視直径)は距離に反比例するので約2倍
  - 計算方法・前提: 視直径 ≈ 直径/距離。距離1/2 → 視直径2倍。
- **[仮定]** 潮位差も8倍になる
  - 注記: 実際の潮位差は海の形・共鳴・摩擦で決まり、起潮力に比例するとは限らない。動画内で『仮定すると』と明示。
- **[確認済みの事実]** 鳴門海峡の潮流は最大時速約20km、播磨灘と紀伊水道の間に最大約1.5mの水位差ができる
  - 出典: 国土交通省 観光庁 多言語解説文データベース（鳴門海峡の渦潮）PDF <https://www.mlit.go.jp/tagengo-db/common/001555540.pdf>
- **[推定・概算]** 潮位差8倍なら流れは約時速55km
  - 計算方法・前提: ベルヌーイの式 v=√(2gΔh)。Δh=1.5m → v≈5.4m/s≈19.6km/h（観測の約20km/hと整合）。Δh=12m → v≈15.3m/s≈55km/h。摩擦・地形・流量制約は無視。
  - 出典: 国土交通省 観光庁 多言語解説文データベース（鳴門海峡の渦潮）PDF <https://www.mlit.go.jp/tagengo-db/common/001555540.pdf>
- **[推定・概算]** 潮流エネルギーは約23倍
  - 計算方法・前提: 運動エネルギー流束は流速の3乗に比例。(55/19.6)^3 ≈ (√8)^3 = 8^1.5 ≈ 22.6 → 約23倍。
- **[確認済みの事実]** 渦潮の直径は大潮時に最大20〜30m程度とされる（動画内では数値を使用せず）
  - 出典: 鳴門市 PRパンフレット <https://www.city.naruto.tokushima.jp/promotion/narutomade/2021/pdf/03-04.pdf>
  - 出典: ANA Japan Travel Planner 徳島（鳴門の渦潮） <https://www.ana.co.jp/ja/au/japan-travel-planner/tokushima/0000001.html>
- **[フィクション]** 徳島が渦潮発電で世界のエネルギー首都になる
  - 注記: オチのためのフィクション。『！？』を付け、キャプションでも思考実験と明記。

## 出典一覧

| ID | タイトル | URL | 参照日 | 用途 |
|---|---|---|---|---|
| nasa_moon_facts | NASA Science - Moon Facts | https://science.nasa.gov/moon/facts/ | 2026-10-28 | 月の平均距離 384,400 km |
| jpl_ld | NASA JPL CNEOS - LD (Lunar Distance) | https://cneos.jpl.nasa.gov/glossary/LD.html | 2026-10-28 | 1月距離(LD)=平均半長径384,400 km |
| tidal_textbook | Universe (Freedman et al.) Box 10-1 Calculating Tidal Forces | https://digfir-published.macmillanusa.com/universe10e/asset/boxes/10_1.html | 2026-10-28 | 潮汐力は距離の3乗に反比例（距離2倍で1/8） |
| mlit_naruto | 国土交通省 観光庁 多言語解説文データベース（鳴門海峡の渦潮）PDF | https://www.mlit.go.jp/tagengo-db/common/001555540.pdf | 2026-10-28 | 最大時速約20km、最大1.5mの水位差、海峡幅1.3km |
| naruto_city_pdf | 鳴門市 PRパンフレット | https://www.city.naruto.tokushima.jp/promotion/narutomade/2021/pdf/03-04.pdf | 2026-10-28 | 渦の直径 最大約30m（参考） |
| ana_naruto | ANA Japan Travel Planner 徳島（鳴門の渦潮） | https://www.ana.co.jp/ja/au/japan-travel-planner/tokushima/0000001.html | 2026-10-28 | 渦の直径20m、時速20km以上（参考・二次情報） |

## 素材のライセンス

- 地図: Natural Earth（パブリックドメイン） https://www.naturalearthdata.com/
- フォント: Dela Gothic One / Noto Sans JP（SIL Open Font License 1.1）
- BGM・効果音: コードで手続き生成（第三者素材なし）
- ナレーション: Open JTalk + HTS voice "Mei"（CC BY 3.0, Nagoya Institute of Technology） → キャプションにクレジット記載
