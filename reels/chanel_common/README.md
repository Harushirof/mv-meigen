# シャネル版 共通の背景画像

シャネル版の動画は、すべてこの画像1枚を背景に使う（2026-11-04 HF決定）。

- `background.png`：背景画像（AIで生成、941×1672）
- 字幕は人物の反対側の右寄せ（`config.json` の `"style": {"text_x": 0.68}`）、画像の明るさは `"brightness": 0.6`
- 新しい動画は `chanel/posts/NN_スラッグ/` に作る（`chanel/README.md`）。config.json は `chanel/posts/01_erabareru-onna/config.json` をコピーし、`"photos": ["../../../reels/chanel_common/background.png"]` のまま使う

画像を差し替えるときは、このファイルを上書きする。
