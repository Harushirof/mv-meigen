#!/usr/bin/env python3
"""シャネル版の音声を作る（Cartesia「Rachel」）。

narration.txt を1文ずつ読み上げ、文の間に無音を入れてつなぎ、BGM を混ぜる。
既定値は1本目（01_erabareru-onna）と同じ：速さ0.8、文の間0.6秒、BGM音量0.14、冒頭1秒・末尾2秒の余白。

使い方:
  python chanel/tool/make_voice.py chanel/posts/02_xxx
  python chanel/tool/make_voice.py chanel/posts/02_xxx --bgm 10CentsForRestart

出力（投稿フォルダの中）:
  narration.wav   声だけ
  mix.mp3         BGM入り（動画にはこれを使う）
  timings.csv     各文の開始・終了秒（声だけの音声での時刻。動画では冒頭の余白分ずらす）
  voice_parts/    1文ごとの音声（作り直すとき、文が同じならAPIを呼ばずに使い回す）
  voice_report.json

必要なもの: Python 3.9+、requests、ffmpeg（PATH）、リポジトリ直下の .env に CARTESIA_API_KEY
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parents[2]
BGM_DIR = REPO / "chanel" / "bgm"
VOICE_ID = "10bd4af4-825b-49b8-b8bd-0ca11865536e"  # Cartesia「Rachel」
MODEL = "sonic-3.6"
API_VERSION = "2026-08-14"
SR = 24000


def load_key():
    if os.environ.get("CARTESIA_API_KEY"):
        return os.environ["CARTESIA_API_KEY"].strip()
    for env in (REPO / ".env", REPO / "tts_compare" / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8-sig").splitlines():
                if line.strip().startswith("CARTESIA_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"')
    sys.exit("CARTESIA_API_KEY が見つかりません。リポジトリ直下の .env に CARTESIA_API_KEY=... を書いてください")


def split_sentences(text):
    """1行ずつ見て「。」で文に分ける（render_reel.py と telop.txt の1行＝1文に合わせる）。"""
    return [s.strip() for line in text.splitlines() for s in re.findall(r"[^。]+。?", line.strip()) if s.strip()]


def synth(key, text, speed):
    body = {"model_id": MODEL, "transcript": text, "voice": {"id": VOICE_ID}, "language": "ja",
            "generation_config": {"speed": speed},
            "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": SR}}
    headers = {"Authorization": f"Bearer {key}", "Cartesia-Version": API_VERSION}
    for attempt in range(5):
        r = requests.post("https://api.cartesia.ai/tts/bytes", headers=headers, json=body, timeout=180)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(10 * (attempt + 1))
            continue
        if not r.ok:
            sys.exit(f"Cartesia エラー {r.status_code}: {r.text[:300]}")
        return r.content
    sys.exit("Cartesia が混み合っていて生成できませんでした。時間をおいて再実行してください")


def read_pcm(b):
    with wave.open(io.BytesIO(b)) as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2 or w.getframerate() != SR:
            sys.exit(f"想定外の音声形式です: {w.getparams()}")
        return w.readframes(w.getnframes())


def find_bgm(name):
    hits = sorted(p for p in BGM_DIR.glob(f"{name}.*") if p.suffix.lower() in (".mp3", ".wav", ".m4a"))
    if not hits:
        sys.exit(f"BGM が見つかりません: {BGM_DIR / (name + '.mp3')}（chanel/bgm/README.md を参照）")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post_dir")
    ap.add_argument("--bgm", default="ShinshiiAsa", help="chanel/bgm/ の曲名（拡張子なし）。none でBGMなし")
    ap.add_argument("--speed", type=float, default=0.8)
    ap.add_argument("--gap", type=float, default=0.6, help="文と文の間の無音（秒）")
    ap.add_argument("--bgm-volume", type=float, default=0.14)
    ap.add_argument("--lead", type=float, default=1.0, help="声が始まる前のBGMだけの秒数")
    ap.add_argument("--tail", type=float, default=2.0, help="声が終わった後のBGMの秒数（この間にフェードアウト）")
    a = ap.parse_args()

    post = Path(a.post_dir).resolve()
    sentences = split_sentences((post / "narration.txt").read_text(encoding="utf-8-sig"))
    if not sentences:
        sys.exit("narration.txt が空です")
    telop = post / "telop.txt"
    if telop.exists():
        rows = [l for l in telop.read_text(encoding="utf-8-sig").splitlines() if l.strip() and not l.startswith("#")]
        if len(rows) != len(sentences):
            sys.exit(f"telop.txt の行数（{len(rows)}）と narration.txt の文の数（{len(sentences)}）が合いません。"
                     "telop.txt は1行＝1文にしてください")

    key = None
    parts_dir = post / "voice_parts"
    parts_dir.mkdir(exist_ok=True)
    pcms, api_chars = [], 0
    for i, s in enumerate(sentences, 1):
        h = hashlib.sha1(f"{VOICE_ID}|{MODEL}|{a.speed}|{s}".encode()).hexdigest()[:10]
        f = parts_dir / f"{i:03d}_{h}.wav"
        if not f.exists():
            key = key or load_key()
            for old in parts_dir.glob(f"{i:03d}_*.wav"):
                old.unlink()
            f.write_bytes(synth(key, s, a.speed))
            api_chars += len(s)
            print(f"[{i}/{len(sentences)}] {s}", flush=True)
        pcms.append(read_pcm(f.read_bytes()))

    rows, t = [], 0.0
    silence = b"\x00\x00" * int(SR * a.gap)
    with wave.open(str(post / "narration.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for i, (data, s) in enumerate(zip(pcms, sentences), 1):
            w.writeframes(data)
            d = len(data) / 2 / SR
            rows.append([i, f"{t:.3f}", f"{t + d:.3f}", s])
            t += d
            if i < len(pcms):
                w.writeframes(silence)
                t += len(silence) / 2 / SR
    with open(post / "timings.csv", "w", encoding="utf-8", newline="") as fh:
        cw = csv.writer(fh)
        cw.writerow(["index", "start_sec", "end_sec", "text"])
        cw.writerows(rows)

    total = a.lead + t + a.tail
    voice = ["-i", str(post / "narration.wav")]
    delay = int(a.lead * 1000)
    if a.bgm.lower() == "none":
        flt = f"[0:a]adelay={delay},apad,atrim=0:{total:.3f},aresample=44100,pan=stereo|c0=c0|c1=c0[out]"
        inputs = voice
    else:
        inputs = voice + ["-stream_loop", "-1", "-i", str(find_bgm(a.bgm))]
        flt = (f"[0:a]aresample=44100,pan=stereo|c0=c0|c1=c0,adelay={delay}|{delay},apad[v];"
               f"[1:a]aresample=44100,aformat=channel_layouts=stereo,volume={a.bgm_volume},"
               f"atrim=0:{total:.3f},afade=t=out:st={max(total - a.tail, 0):.3f}:d={a.tail}[b];"
               f"[v][b]amix=inputs=2:duration=shortest:normalize=0[out]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", flt, "-map", "[out]",
                    "-t", f"{total:.3f}", "-c:a", "libmp3lame", "-b:a", "192k", str(post / "mix.mp3")], check=True)

    rep = dict(voice="Rachel", speed=a.speed, gap_sec=a.gap, bgm=a.bgm, bgm_volume=a.bgm_volume,
               lead_sec=a.lead, tail_sec=a.tail, sentences=len(sentences),
               chars=sum(len(re.sub(r"\s", "", s)) for s in sentences),
               voice_sec=round(t, 2), mix_sec=round(total, 2), api_chars_this_run=api_chars)
    (post / "voice_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
