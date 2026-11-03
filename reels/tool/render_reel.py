#!/usr/bin/env python3
"""偉人の手帳 縦型動画レンダラー

台本の音声（narration_full.wav）と文ごとのタイミング（timings.csv）から、
1080x1920 / 30fps の縦型動画を作る。

画面構成
- 背景：白黒の写真をゆっくり拡大（複数枚を均等に切り替え）、暗めに調整
- 上部：半透明の白帯に「名前」と「生没年」
- 冒頭：タイトルを3行・3色の極太ゴシックで大きく表示（1文目の読み上げ中）
- 本文：白い太字明朝・黒フチの縦書きテロップを1フレーズずつ表示

必要なもの：Python 3.9+、Pillow、ffmpeg（PATHに通っていること）
使い方：python render_reel.py config.json
設定例：reels/new02_chanel_tiktok/config.json（photos が空なら仮の暗い背景で書き出す）
"""
import csv
import json
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
SERIF = os.path.join(FONT_DIR, "NotoSerifJP_900Black.ttf")
SERIF_BAND = os.path.join(FONT_DIR, "NotoSerifJP_700Bold.ttf")
GOTHIC = os.path.join(FONT_DIR, "DelaGothicOne_400Regular.ttf")

# 縦書きで向きを変える文字
VERT_MAP = {"ー": "丨", "―": "丨", "－": "丨", "-": "丨", "…": "︙", "「": "﹁", "」": "﹂",
            "『": "﹃", "』": "﹄", "（": "︵", "）": "︶", "(": "︵", ")": "︶", "〜": "丨", "~": "丨"}
DROP = set("、。，．,.？?！!　 ")
TITLE_COLORS = [(255, 214, 0), (230, 20, 30), (40, 200, 60)]


def split_telop(sentence, max_len=16):
    """1文を、テロップ1枚あたり max_len 文字以内に区切る。読点で区切り、長ければ助詞の後ろで切る。"""
    out = []
    for chunk in re.split(r"(?<=[、。？！?!])", sentence):
        clean = "".join(c for c in chunk if c not in DROP)
        while len(clean) > max_len:
            cut = None
            for i in range(min(max_len, len(clean) - 4), 5, -1):
                if clean[i - 1] in "はがをにでとものへやてばらど":
                    cut = i
                    break
            cut = cut or max_len - 2
            out.append(clean[:cut])
            clean = clean[cut:]
        if clean:
            out.append(clean)
    return out


def vertical_columns(text, per_col):
    cols, cur = [], ""
    for ch in text:
        cur += ch
        if len(cur) >= per_col:
            cols.append(cur)
            cur = ""
    if cur:
        cols.append(cur)
    return cols


def draw_vertical(draw, text, font, center_x, top_y, size, fill, stroke, stroke_fill, per_col=10, col_gap=1.15):
    """縦書き。列は右から左へ。center_x は列群全体の中心。"""
    cols = vertical_columns(text, per_col)
    n = len(cols)
    col_w = size * col_gap
    first_x = center_x + (n - 1) * col_w / 2
    for ci, col in enumerate(cols):
        x = first_x - ci * col_w
        y = top_y
        for ch in col:
            g = VERT_MAP.get(ch, ch)
            small = ch in "ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮ"
            ox = size * 0.12 if small else 0
            oy = -size * 0.12 if small else 0
            draw.text((x + ox, y + oy), g, font=font, fill=fill, anchor="mt",
                      stroke_width=stroke, stroke_fill=stroke_fill)
            y += size * 1.02


def make_telop_overlay(text, cache={}):
    if text in cache:
        return cache[text]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = 104
    per_col = 10 if len(text) <= 20 else 12
    if len(text) > per_col * 2:
        size = 92
    font = ImageFont.truetype(SERIF, size)
    rows = min(len(text), per_col)
    top = max(330, int(H * 0.5 - rows * size * 1.02 / 2) - 80)
    draw_vertical(d, text, font, W / 2, top, size, (255, 255, 255), 10, (0, 0, 0), per_col=per_col)
    cache[text] = img
    return img


def make_title_overlay(lines):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    longest = max(len(l) for l in lines)
    size = min(150, int((H - 520) / max(longest, 1) / 1.02))
    font = ImageFont.truetype(GOTHIC, size)
    col_w = size * 1.12
    n = len(lines)
    first_x = W / 2 + (n - 1) * col_w / 2
    for i, line in enumerate(lines):
        x = first_x - i * col_w
        y = 320
        color = TITLE_COLORS[i % len(TITLE_COLORS)]
        for ch in line:
            g = VERT_MAP.get(ch, ch)
            d.text((x, y), g, font=font, fill=color, anchor="mt", stroke_width=14, stroke_fill=(0, 0, 0))
            y += size * 1.02
    return img


def make_band(name, years):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((90, 70, W - 90, 290), radius=36, fill=(255, 255, 255, 200))
    f1 = ImageFont.truetype(SERIF_BAND, 78)
    f2 = ImageFont.truetype(SERIF_BAND, 70)
    d.text((W / 2, 120), name, font=f1, fill=(0, 0, 0), anchor="mt")
    d.text((W / 2, 205), years, font=f2, fill=(0, 0, 0), anchor="mt")
    return img


def prep_photo(path, grayscale=True, brightness=0.72):
    """暗め・9:16に合わせて少し大きめに切り出す（拡大の余白用）。grayscale=True で白黒にする。"""
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("L" if grayscale else "RGB")
    im = ImageOps.autocontrast(im, cutoff=1)
    im = im.point(lambda v: int(v * brightness))
    base_w, base_h = int(W * 1.15), int(H * 1.15)
    im = ImageOps.fit(im, (base_w, base_h), Image.LANCZOS, centering=(0.5, 0.35))
    return im.convert("RGB")


def placeholder_bg():
    """画像がまだ無いときの仮背景（暗いグレーのグラデーション）。"""
    base_w, base_h = int(W * 1.15), int(H * 1.15)
    grad = Image.linear_gradient("L").resize((base_w, base_h)).point(lambda v: 25 + int(v * 0.12))
    return grad.convert("RGB")


def frame_bg(photo, t_in_seg, seg_len):
    """ゆっくり拡大（1.0→1.08）。"""
    z = 1.0 + 0.08 * (t_in_seg / max(seg_len, 0.001))
    bw, bh = photo.size
    cw, ch = int(bw / z / 1.15 * 1.0), int(bh / z / 1.15 * 1.0)
    cw, ch = min(cw, bw), min(ch, bh)
    x0 = (bw - cw) // 2
    y0 = int((bh - ch) * 0.35)
    return photo.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)


def load_timings(path, offset=0.0):
    """offset：音声の頭に無音やBGMだけの区間がある場合、その秒数だけ後ろにずらす。"""
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append((float(r["start_sec"]) + offset, float(r["end_sec"]) + offset, r["text"]))
    return rows


def build_schedule(timings, title_lines):
    """(開始, 終了, 種類, 内容) のリスト。1文目はタイトル表示、以降は文字数比で各テロップに時間を配分。"""
    sched = []
    for i, (s, e, text) in enumerate(timings):
        if i == 0:
            sched.append((s, e, "title", title_lines))
            continue
        units = split_telop(text)
        total = sum(len(u) for u in units) or 1
        t = s
        for u in units:
            d = (e - s) * len(u) / total
            sched.append((t, t + d, "telop", u))
            t += d
    return sched


def main(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(cfg_path))
    p = lambda x: x if os.path.isabs(x) else os.path.join(base, x)
    audio = p(cfg["audio"])
    timings = load_timings(p(cfg["timings"]), float(cfg.get("timing_offset", 0)))
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", audio],
        capture_output=True, text=True).stdout.strip())
    gray = cfg.get("grayscale", True)
    photos = [prep_photo(p(x), gray, float(cfg.get("brightness", 0.72))) for x in cfg.get("photos", [])]
    photos = photos or [placeholder_bg()]
    seg = duration / len(photos)
    band = make_band(cfg["name"], cfg["years"])
    title = make_title_overlay(cfg["title_lines"])
    sched = build_schedule(timings, cfg["title_lines"])
    out = p(cfg.get("output", "reel.mp4"))

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", audio, "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out,
    ], stdin=subprocess.PIPE)

    n_frames = int(math.ceil(duration * FPS))
    si = 0
    for fi in range(n_frames):
        t = fi / FPS
        k = min(int(t // seg), len(photos) - 1)
        frame = frame_bg(photos[k], t - k * seg, seg).convert("RGBA")
        frame.alpha_composite(band)
        # 次のテロップが始まるまでは今のテロップを出し続ける（文と文の間の無音で消えないように）
        while si + 1 < len(sched) and t >= sched[si + 1][0] - 0.05:
            si += 1
        s, e, kind, content = sched[si]
        if s - 0.05 <= t <= e + 0.6:
            frame.alpha_composite(title if kind == "title" else make_telop_overlay(content))
        ff.stdin.write(frame.convert("RGB").tobytes())
        if fi % (FPS * 10) == 0:
            print(f"{t:6.1f}s / {duration:.1f}s", flush=True)
    ff.stdin.close()
    ff.wait()
    print("done:", out)


if __name__ == "__main__":
    main(sys.argv[1])
