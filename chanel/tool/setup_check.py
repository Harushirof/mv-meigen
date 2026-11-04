#!/usr/bin/env python3
"""シャネル版の制作に必要なものがそろっているかを確かめる。足りないフォントは取りに行く。

使い方: python chanel/tool/setup_check.py
"""
import io
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FONT_DIR = REPO / "reels" / "tool" / "fonts"
# (ファイル名, npm パッケージ名, パッケージ内のパス)
FONTS = [
    ("ShipporiMincho_500Medium.ttf", "shippori-mincho", "500Medium/ShipporiMincho_500Medium.ttf"),
    ("NotoSerifJP_700Bold.ttf", "noto-serif-jp", "700Bold/NotoSerifJP_700Bold.ttf"),
]
ok = True


def report(good, msg, fix=""):
    global ok
    ok &= good
    print(("[OK]  " if good else "[NG]  ") + msg + ("" if good or not fix else f"\n      → {fix}"))


def fetch_font(name, pkg, inner):
    urls = [f"https://cdn.jsdelivr.net/npm/@expo-google-fonts/{pkg}/{inner}",
            f"https://unpkg.com/@expo-google-fonts/{pkg}/{inner}"]
    for u in urls:
        try:
            data = urllib.request.urlopen(u, timeout=60).read()
            if len(data) > 100_000:
                return data
        except Exception:
            pass
    # 最後の手段：npm のパッケージ一式を落として中から取り出す（数十MB）
    import json
    meta = json.load(urllib.request.urlopen(f"https://registry.npmjs.org/@expo-google-fonts/{pkg}", timeout=60))
    tgz = meta["versions"][meta["dist-tags"]["latest"]]["dist"]["tarball"]
    with tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(tgz, timeout=600).read())) as tf:
        return tf.extractfile(f"package/{inner}").read()


print(f"Python {sys.version.split()[0]}")
report(sys.version_info >= (3, 9), "Python 3.9 以上", "Python を新しくする")

try:
    import PIL
    from PIL import features
    report(True, f"Pillow {PIL.__version__}")
    raqm = features.check("raqm")
    print(("[OK]  " if raqm else "[注意] ") + "縦書き組版（raqm）" +
          ("" if raqm else "：無いので1文字ずつ並べる方式で描く。小さい「っ」や「ー」の位置が1本目と少し変わる"))
except ImportError:
    report(False, "Pillow", "pip install pillow requests")
try:
    import requests  # noqa: F401
    report(True, "requests")
except ImportError:
    report(False, "requests", "pip install pillow requests")

for exe in ("ffmpeg", "ffprobe"):
    path = shutil.which(exe)
    report(bool(path), f"{exe}: {path or '見つからない'}", "ffmpeg をインストールして PATH を通す（Windows: winget install Gyan.FFmpeg）")
if shutil.which("ffmpeg"):
    enc = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    report("libx264" in enc and "libmp3lame" in enc, "ffmpeg の libx264・libmp3lame", "フル版の ffmpeg を入れる")

FONT_DIR.mkdir(parents=True, exist_ok=True)
for name, pkg, inner in FONTS:
    f = FONT_DIR / name
    if not f.exists():
        try:
            f.write_bytes(fetch_font(name, pkg, inner))
            print(f"      {name} を取得しました")
        except Exception as e:
            print(f"      {name} の取得に失敗: {e}")
    report(f.exists(), f"フォント {name}", f"HFさんのPCの mv-kakuei\\reels\\tool\\fonts\\{name} を {FONT_DIR} にコピー")

bgm = REPO / "chanel" / "bgm"
songs = sorted(p.stem for p in bgm.glob("*.mp3"))
report("ShinshiiAsa" in songs, f"BGM: {', '.join(songs) or 'なし'}", "chanel/bgm/README.md のとおり曲を置く")

env = REPO / ".env"
has_key = env.exists() and any(l.strip().startswith("CARTESIA_API_KEY=") and len(l.split("=", 1)[1].strip()) > 5
                               for l in env.read_text(encoding="utf-8-sig").splitlines())
report(has_key, ".env の CARTESIA_API_KEY", f"{env} に CARTESIA_API_KEY=... を書く")

print("\nすべてそろっています" if ok else "\n[NG] の項目を直してから、もう一度実行してください")
sys.exit(0 if ok else 1)
