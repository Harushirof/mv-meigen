"""Gemini と Cartesia で同じ台本を読み上げて比較する。

使い方:
  python -I gen.py samples                    タイトル行を各社8声で生成
  python -I gen.py full PROVIDER SCRIPT VOICE  全文を生成（SCRIPT: m01 | f02）
"""
import base64
import csv
import io
import json
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
ENV = dict(l.split("=", 1) for l in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if "=" in l and not l.startswith("#"))
GEMINI_KEY = ENV["GEMINI_API_KEY"].strip()
CARTESIA_KEY = ENV["CARTESIA_API_KEY"].strip()
LOG = ROOT / "api_log.jsonl"
SR = 24000
TARGET_CPS = 5.7
GAP = 0.3

SCRIPTS = {
    "m01": dict(
        file="script_m01.txt", title="頭のいい奴より、頭を下げられる奴になれ。",
        style=("an elderly Japanese man narrating in Japanese, slightly husky voice, firm and admonishing tone, "
               "calm measured pace with short pauses between phrases")),
    "f02": dict(
        file="script_f02.txt", title="選ばれる女より、自分で選ぶ女になりなさい。",
        style=("a mature Japanese woman narrating in Japanese, calm, elegant and dignified, firm but warm tone, "
               "measured pace with short pauses between phrases")),
}
VOICES = {
    "gemini": {"f02": ["Gacrux", "Sulafat", "Kore", "Vindemiatrix"]},
    "cartesia": {"f02": {"Yuki": "59d4fd2f-f5eb-4410-8105-58db7661144f",
                         "Valerie": "af346552-54bf-4c2b-a4d4-9d2820f51b6c",
                         "Yuzuki": "cb21b4af-0e46-44f7-9128-51be7f898311",
                         "Aiko": "498e7f37-7fa3-4e2c-b8e2-8b6e9276f956"}},
}


def log(**kw):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def post(url, headers, body):
    for attempt in range(5):
        r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(15 * (attempt + 1))
            continue
        if not r.ok:
            raise RuntimeError(f"{r.status_code} {r.text[:300]}")
        return r
    raise RuntimeError("retries exhausted")


def to_wav(raw):
    if raw[:4] == b"RIFF":
        return raw
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(raw)
    return buf.getvalue()


def gemini(text, voice, style):
    body = {"model": "gemini-3.8-flash-tts",
            "input": [{"type": "user_input", "content": [{
                "type": "text", "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}]}]}],
            "response_format": {"type": "audio", "mime_type": "audio/wav"},
            "generation_config": {"speech_config": [{"voice": voice}]}}
    j = post("https://generativelanguage.googleapis.com/v1beta/interactions",
             {"x-goog-api-key": GEMINI_KEY}, body).json()
    log(provider="gemini", voice=voice, text=text, usage=j.get("usage"))
    audio = [c for s in j["steps"] if s["type"] == "model_output" for c in s["content"] if c["type"] == "audio"]
    return to_wav(base64.b64decode(audio[-1]["data"]))


def cartesia(text, voice_id):
    body = {"model_id": "sonic-3.6", "transcript": text, "voice": {"id": voice_id}, "language": "ja",
            "output_format": {"container": "wav", "encoding": "pcm_s16le", "sample_rate": SR}}
    r = post("https://api.cartesia.ai/tts/bytes",
             {"Authorization": f"Bearer {CARTESIA_KEY}", "Cartesia-Version": "2026-08-14"}, body)
    log(provider="cartesia", voice=voice_id, text=text, chars=len(text))
    return to_wav(r.content)


def synth(provider, text, voice, script):
    if provider == "gemini":
        return gemini(text, voice, SCRIPTS[script]["style"])
    return cartesia(text, VOICES["cartesia"][script][voice])


def pcm(b):
    with wave.open(io.BytesIO(b)) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, w.getparams()
        return w.getframerate(), w.readframes(w.getnframes())


def dur(b):
    fr, data = pcm(b)
    return len(data) / 2 / fr


def tempo(b, factor, tmp):
    src, dst = tmp / "in.wav", tmp / "out.wav"
    src.write_bytes(b)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter:a",
                    f"rubberband=tempo={factor:.4f}", "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", str(dst)],
                   check=True)
    return dst.read_bytes()


def samples():
    for provider in ("gemini", "cartesia"):
        out = ROOT / provider / "samples"
        out.mkdir(parents=True, exist_ok=True)
        for script, voices in VOICES[provider].items():
            for v in voices:
                b = synth(provider, SCRIPTS[script]["title"], v, script)
                (out / f"{script}_{v}.wav").write_bytes(b)
                print(provider, script, v, round(dur(b), 2), flush=True)


def full(provider, script, voice):
    out = ROOT / provider / f"{script}_{voice}"
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "parts").mkdir(exist_ok=True)
    text = (ROOT / SCRIPTS[script]["file"]).read_text(encoding="utf-8")
    sentences = [s.strip() for line in text.splitlines() for s in re.findall(r"[^。]+。?", line.strip()) if s.strip()]
    nchars = sum(len(re.sub(r"\s", "", s)) for s in sentences)

    raws = []
    for i, s in enumerate(sentences, 1):
        b = synth(provider, s, voice, script)
        if pcm(b)[0] != SR:
            b = tempo(b, 1.0, out)
        (out / "raw" / f"{i:03d}.wav").write_bytes(b)
        raws.append(b)
    speech = sum(dur(b) for b in raws)
    factor = speech / (nchars / TARGET_CPS - GAP * (len(sentences) - 1))
    parts = [tempo(b, factor, out) for b in raws]

    rows, t = [], 0.0
    with wave.open(str(out / "narration_full.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for i, (b, s) in enumerate(zip(parts, sentences), 1):
            (out / "parts" / f"{i:03d}.wav").write_bytes(b)
            _, data = pcm(b)
            w.writeframes(data)
            d = len(data) / 2 / SR
            rows.append([i, f"{t:.3f}", f"{t + d:.3f}", s])
            t += d
            if i < len(parts):
                w.writeframes(b"\x00\x00" * int(SR * GAP))
                t += GAP
    with open(out / "timings.csv", "w", encoding="utf-8", newline="") as f:
        cw = csv.writer(f)
        cw.writerow(["index", "start_sec", "end_sec", "text"])
        cw.writerows(rows)
    for p in ("in.wav", "out.wav"):
        (out / p).unlink(missing_ok=True)
    rep = dict(provider=provider, script=script, voice=voice, sentences=len(sentences), chars=nchars,
               raw_speech_sec=round(speech, 2), tempo=round(factor, 3), gap_sec=GAP,
               total_sec=round(t, 2), cps=round(nchars / t, 3))
    (out / "report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "samples":
        samples()
    else:
        full(*sys.argv[2:5])
