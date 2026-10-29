"""Japanese narration synthesis.

Backends
  openjtalk : offline, free. Voice "Mei" (CC BY 3.0, Nagoya Institute of Technology) -> credit required.
  google    : Google Cloud Text-to-Speech REST (needs GOOGLE_TTS_API_KEY). Higher quality.
              NOTE: not exercised from the development sandbox (network policy); verify on first Actions run.
  gemini    : Gemini API speech generation (needs GEMINI_API_KEY). Prebuilt voices + natural-language style.
              Model names change often: GEMINI_TTS_MODEL is tried first, then any TTS model ListModels reports.
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
    "gemini": "ナレーション: AI音声（Google Gemini）",
}

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL_PREFERENCE = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]
_gemini_model: str | None = None
_gemini_tried: set[str] = set()


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


def gemini_tts_models() -> list[str]:
    """TTS-capable models visible to this API key, preferred ones first."""
    import requests

    r = requests.get(f"{GEMINI_API}/models", params={"key": os.environ["GEMINI_API_KEY"], "pageSize": 200}, timeout=30)
    r.raise_for_status()
    names = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
             if "tts" in m["name"] and "generateContent" in m.get("supportedGenerationMethods", [])]
    return sorted(names, key=lambda n: (GEMINI_MODEL_PREFERENCE.index(n) if n in GEMINI_MODEL_PREFERENCE else 99, n))


def _gemini_call(model: str, text: str, voice: str, style: str):
    import requests

    prompt = f"{style}: {text}" if style else text
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    return requests.post(f"{GEMINI_API}/models/{model}:generateContent", params={"key": os.environ["GEMINI_API_KEY"]},
                         json=body, timeout=120)


def synth_gemini(text: str, voice: str = "Charon", style: str = "") -> np.ndarray:
    import time

    global _gemini_model
    if _gemini_model is None:
        _gemini_model = os.environ.get("GEMINI_TTS_MODEL") or GEMINI_MODEL_PREFERENCE[0]
    for attempt in range(8):
        r = _gemini_call(_gemini_model, text, voice, style)
        if r.status_code == 404 and attempt == 0:  # model retired/renamed: pick one the API offers
            found = gemini_tts_models()
            if not found:
                raise RuntimeError("no Gemini TTS model available for this API key")
            print(f"Gemini TTS model {_gemini_model} not found; using {found[0]} (available: {found})")
            _gemini_model = found[0]
            continue
        if r.status_code == 402:  # this model needs paid credits on this project: try another TTS model
            others = [m for m in gemini_tts_models() if m not in _gemini_tried]
            _gemini_tried.add(_gemini_model)
            others = [m for m in others if m not in _gemini_tried]
            if not others:
                raise RuntimeError(f"Gemini TTS 402 (no credits) for every TTS model tried: {sorted(_gemini_tried)}")
            print(f"Gemini TTS model {_gemini_model} needs credits (402); trying {others[0]}")
            _gemini_model = others[0]
            continue
        if r.status_code in (429, 500, 503):  # rate limit / transient: bounded backoff
            time.sleep(min(60, 5 * 2 ** attempt))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Gemini TTS {r.status_code}: {r.text[:300]}")
        part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        pcm = np.frombuffer(base64.b64decode(part["data"]), dtype=np.int16).astype(np.float32) / 32768.0
        rate = int(next((p.split("=")[1] for p in part.get("mimeType", "").split(";") if p.strip().startswith("rate=")),
                        24000))
        return _resample(pcm, rate)
    raise RuntimeError("Gemini TTS kept failing (rate limit or server errors)")


def gemini_probe() -> dict[str, str]:
    """Try a one-word request on every TTS model: {model: 'OK' | 'HTTP <code>'} (for preflight)."""
    out = {}
    for m in gemini_tts_models():
        r = _gemini_call(m, "テスト", "Charon", "")
        out[m] = "OK" if r.status_code == 200 else f"HTTP {r.status_code}"
    return out


def gemini_model_used() -> str | None:
    return _gemini_model


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
    elif backend == "gemini":
        x = synth_gemini(text, **kw)
    else:
        raise ValueError(f"unknown TTS backend {backend}")
    x = _trim(x)
    peak = float(np.max(np.abs(x))) or 1.0
    x = (x / peak * 0.89).astype(np.float32)
    np.save(f, x)
    return x
