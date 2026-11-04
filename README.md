# mv-meigen

偉人の名言を使った縦型リール（Facebook、TikTok）の制作物。

## 構成

| パス | 中身 |
|---|---|
| `reels/sample_reel_*.md` | 参考にした既存リールの書き起こしと台本 |
| `reels/new01/` | 1本目の台本、ナレーション、テロップ（SRT と一覧） |
| `reels/new01_tiktok/`、`reels/new02_chanel_tiktok/` | TikTok 向けの短尺ナレーション |
| `reels/skill/SKILL.md` | 台本を作る Skill |
| `reels/tool/render_reel.py` | 縦型動画のレンダラー |
| `chanel/`、`.claude/skills/chanel-*` | シャネル版を Claude Code で作る一式（`chanel/README.md`） |
| `tts_compare/` | Gemini と Cartesia の音声合成を比べるスクリプト |

## Git に入れていないもの

- `.env`（`GEMINI_API_KEY`、`CARTESIA_API_KEY`）。`tts_compare/.env` に各自で置く
- 音声（mp3、wav）と動画
- フォント。`reels/tool/fonts/` に次の3つを Google Fonts から取得して置く
  - `NotoSerifJP_900Black.ttf`、`NotoSerifJP_700Bold.ttf`（Noto Serif JP）
  - `DelaGothicOne_400Regular.ttf`（Dela Gothic One）
