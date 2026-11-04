---
name: chanel-voice
description: シャネル動画の台本（narration.txt）から、Cartesia「Rachel」の声とBGM入りの音声（mix.mp3）と文ごとの時刻（timings.csv）を作るときに使う。chanel-script の次に使う。
---

# シャネル動画 ② 音声づくり

`chanel/tool/make_voice.py` で、台本を1文ずつ Cartesia の「Rachel」で読み上げ、BGM を混ぜる。
設定は1本目と同じ：速さ0.8、文の間0.6秒、BGM「ShinshiiAsa」を音量0.14、冒頭1秒・末尾2秒（フェードアウト）。

## 入力
- 投稿フォルダ `chanel/posts/NN_スラッグ/` の `narration.txt`（と `telop.txt`）
- リポジトリ直下の `.env` に `CARTESIA_API_KEY=...`
- `chanel/bgm/ShinshiiAsa.mp3`（置き方は `chanel/bgm/README.md`）

## 進め方
1. 初めての PC なら `python chanel/tool/setup_check.py` を実行し、[NG] が無いことを確かめる。
2. 台本の OK をもらっていることを確かめる（Cartesia は文字数に応じて料金がかかる）。
3. 実行する：
   ```
   python chanel/tool/make_voice.py chanel/posts/NN_スラッグ
   ```
   BGM を変えるときは `--bgm 10CentsForRestart`、BGM なしは `--bgm none`。
4. 出力された `voice_report.json` を確認して報告する：`voice_sec`（声の長さ）、`mix_sec`（全体の長さ）、`api_chars_this_run`（今回 API に送った文字数）。
5. 一部の文だけ直したいときは narration.txt と telop.txt の該当文を直して再実行する。変わっていない文は `voice_parts/` の音声を使い回すので、API は直した文の分しか呼ばない。

## 出力（投稿フォルダの中）
| ファイル | Git |
|---|---|
| `timings.csv`（各文の開始・終了秒） | 上げる |
| `narration.wav`（声だけ）、`mix.mp3`（BGM入り）、`voice_parts/`、`voice_report.json` | 上げない（.gitignore 済み） |

## 止まったとき
- 「telop.txt の行数と文の数が合いません」：telop.txt を1行＝1文に直す（`chanel-script` のルール）。
- 「CARTESIA_API_KEY が見つかりません」：`.env` を確認。キーは画面やログに表示しない。
- Cartesia の 401/402：キーの期限切れかプランの上限。依頼者に伝えて止まる。
- 読み間違い（固有名詞など）：その文をひらがなに書き換えて再実行する。字幕の telop.txt は漢字のままでよい。
