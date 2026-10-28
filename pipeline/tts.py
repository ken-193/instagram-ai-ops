"""Japanese narration synthesis.

Backends
  openjtalk : offline, free. Voice "Mei" (CC BY 3.0, Nagoya Institute of Technology) -> credit required.
  google    : Google Cloud Text-to-Speech REST (needs GOOGLE_TTS_API_KEY). Higher quality.
              NOTE: not exercised from the development sandbox (network policy); verify on first Actions run.
"""
from __future__ import annotations

import base64
import hashlib
import io
import os
import wave
from pathlib import Path

import numpy as np

SR = 48000

CREDITS = {
    "openjtalk": "ナレーション音声: Open JTalk / HTS voice \"Mei\" (c) Nagoya Institute of Technology, CC BY 3.0",
    "google": "ナレーション音声: Google Cloud Text-to-Speech",
}


def _resample(x: np.ndarray, sr_in: int, sr_out: int = SR) -> np.ndarray:
    if sr_in == sr_out:
        return x
    n = int(len(x) * sr_out / sr_in)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def _trim(x: np.ndarray, thresh: float = 0.01) -> np.ndarray:
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    pad = int(0.03 * SR)
    return x[max(0, idx[0] - pad): idx[-1] + pad]


def synth_openjtalk(text: str, speed: float = 1.12, half_tone: float = 0.0) -> np.ndarray:
    import pyopenjtalk

    x, sr = pyopenjtalk.tts(text, speed=speed, half_tone=half_tone)
    x = x.astype(np.float32) / 32768.0
    return _resample(x, sr)


def synth_google(text: str, voice: str = "ja-JP-Chirp3-HD-Charon", rate: float = 1.1) -> np.ndarray:
    import requests

    key = os.environ["GOOGLE_TTS_API_KEY"]
    body = {
        "input": {"text": text},
        "voice": {"languageCode": "ja-JP", "name": voice},
        "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": SR, "speakingRate": rate},
    }
    r = requests.post(f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}", json=body, timeout=60)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["audioContent"])
    with wave.open(io.BytesIO(raw)) as w:
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return _resample(pcm, w.getframerate())


def synth(text: str, backend: str, cache_dir: Path, **kw) -> np.ndarray:
    cache_dir.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(f"{backend}|{text}|{sorted(kw.items())}".encode()).hexdigest()[:20]
    f = cache_dir / f"{h}.npy"
    if f.exists():
        return np.load(f)
    if backend == "openjtalk":
        x = synth_openjtalk(text, **kw)
    elif backend == "google":
        x = synth_google(text, **kw)
    else:
        raise ValueError(f"unknown TTS backend {backend}")
    x = _trim(x)
    peak = float(np.max(np.abs(x))) or 1.0
    x = (x / peak * 0.89).astype(np.float32)
    np.save(f, x)
    return x
