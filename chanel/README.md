# シャネル版の動画づくり

TikTok「偉人のひとり言」（@ijin_hitorigoto_coco）のシャネル動画を、Claude Code CLI から作るための一式。

## 作り方

リポジトリのフォルダで Claude Code を起動し、たとえば次のように頼む。

> シャネル動画を作って。テーマは「自分の色を持つこと」

Claude Code は `.claude/skills/` の3つの Skill を順に使う。

| 順 | Skill | やること | 主な出力 |
|---|---|---|---|
| ① | `chanel-script` | テーマから台本を作る（OK をもらってから次へ） | `narration.txt`、`telop.txt`、`caption.md`、`config.json` |
| ② | `chanel-voice` | Cartesia「Rachel」で読み上げ、BGM を混ぜる | `mix.mp3`、`timings.csv` |
| ③ | `chanel-render` | 字幕つき縦型動画とサムネを書き出す | `chanelNN_ShinshiiAsa.mp4`、`thumbnail.png` |

1本ごとに `chanel/posts/NN_スラッグ/` にまとまる。テキスト（台本、字幕、時刻、設定、投稿文）は Git に上げ、音声・動画・サムネは上げない。投稿は手で行う。

## 新しい PC での準備（最初の1回）

1. リポジトリを clone する：`git clone https://github.com/Harushirof/mv-meigen.git`
2. Python 3.9 以上を入れ、`pip install pillow requests`
3. ffmpeg を入れて PATH を通す（Windows：`winget install Gyan.FFmpeg`）
4. BGM を `chanel/bgm/` に置く（`chanel/bgm/README.md`）
5. リポジトリ直下に `.env` を作り、`CARTESIA_API_KEY=...` を書く（Git には上がらない）
6. `python chanel/tool/setup_check.py` を実行する。足りないフォントはここで自動で取りに行く。すべて [OK] なら準備完了

## ファイル

| パス | 中身 |
|---|---|
| `chanel/posts/NN_スラッグ/` | 1本ごとの台本・字幕・設定・投稿文（01 がお手本） |
| `chanel/tool/make_voice.py` | 音声づくり（②） |
| `chanel/tool/setup_check.py` | 準備の確認とフォントの取得 |
| `chanel/bgm/` | BGM 置き場（Git 対象外） |
| `reels/tool/render_reel.py` | 動画とサムネのレンダラー（③） |
| `reels/chanel_common/background.png` | 全動画で共通の背景画像 |
