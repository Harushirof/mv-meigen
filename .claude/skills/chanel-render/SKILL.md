---
name: chanel-render
description: シャネル動画の音声（mix.mp3）と字幕（telop.txt、timings.csv）から、固定背景・縦書き字幕の縦型動画（mp4）とサムネ（PNG）を書き出すときに使う。chanel-voice の次に使う。
---

# シャネル動画 ③ 字幕動画とサムネ

既存のレンダラー `reels/tool/render_reel.py` で、1080×1920・30fps の動画を書き出す。
見た目は1本目と同じ：背景は固定画像 `reels/chanel_common/background.png`（白黒・明るさ0.6）、上部に名前と生没年の帯、冒頭はタイトル、その後は白いしっぽり明朝の縦書き字幕を右寄せ（横位置0.68）で1枚ずつ。

## 入力（投稿フォルダ `chanel/posts/NN_スラッグ/`）
- `config.json`、`telop.txt`、`timings.csv`、`mix.mp3`

## 進め方
1. 先にサムネだけ作って見る（数秒で終わる）：
   ```
   python reels/tool/render_reel.py chanel/posts/NN_スラッグ/config.json --thumbnail-only
   ```
   `thumbnail.png` を開き、タイトルが3列で収まっているか、人物に重なっていないかを確認する。はみ出すときは config.json の `title_lines` の区切りを変える。
2. 動画を書き出す（1分40秒で数分かかる）：
   ```
   python reels/tool/render_reel.py chanel/posts/NN_スラッグ/config.json
   ```
3. 仕上がりを確認する：
   - `ffprobe -v error -show_entries format=duration -of csv=p=0 <動画>` の長さが `voice_report.json` の `mix_sec` とほぼ同じ
   - timings.csv の最後の `end_sec` ＋1秒（冒頭の余白）が、動画の長さより短い
   - 途中のフレームを数枚 PNG に切り出して見る（例 `ffmpeg -ss 30 -i <動画> -frames:v 1 check_30s.png`）。字幕が画面からはみ出していないか、2列の折り返しが言葉の途中で切れていないか
4. 依頼者に動画とサムネの場所を伝える。HFさんの PC で作ったときは `C:\Users\harus\Documents\Dev\mv-chanel\videos\NN_スラッグ\` にコピーする。

## 出力（投稿フォルダの中。Git に上げない）
- `chanelNN_ShinshiiAsa.mp4`（名前は config.json の `output`）
- `thumbnail.png`（TikTok のカバー用。冒頭のタイトル画面と同じ絵）

## 直し方
| 直したいこと | 直す場所 |
|---|---|
| 字幕の区切り・折り返し | `telop.txt`（全角スペースで1枚、「/」で列の折り返し） |
| タイトルの列の分け方 | `config.json` の `title_lines` |
| 字幕の横位置 | `config.json` の `style.text_x`（0＝左、1＝右。シャネル版は0.68で固定） |
| 字幕と声のずれ | 音声を作り直したら timings.csv も変わる。`timing_offset` は make_voice.py の冒頭余白（1.0秒）と同じにする |

## 止まったとき
- 「telop_file の行数が音声の文の数と合いません」：telop.txt を1行＝1文に直す。
- フォントが無いエラー：`python chanel/tool/setup_check.py` を実行する。
- setup_check.py で「縦書き組版（raqm）」が[注意]のときも動画は作れるが、小さい「っ」や「ー」の位置が1本目と少し変わる。
