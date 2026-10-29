import base64

import numpy as np

from pipeline import tts


class Resp:
    def __init__(self, status, payload=None):
        self.status_code, self._p, self.text = status, payload or {}, str(payload)

    def json(self):
        return self._p


def audio_payload(n=2400, rate=24000):
    pcm = (np.sin(np.arange(n) / 5) * 10000).astype(np.int16).tobytes()
    return {"candidates": [{"content": {"parts": [{"inlineData": {
        "mimeType": f"audio/L16;codec=pcm;rate={rate}", "data": base64.b64encode(pcm).decode()}}]}}]}


def test_gemini_parses_pcm_and_resamples(monkeypatch):
    monkeypatch.setattr(tts, "_gemini_model", "m-tts")
    monkeypatch.setattr(tts, "_gemini_call", lambda *a: Resp(200, audio_payload()))
    x = tts.synth_gemini("テスト", voice="Charon")
    assert abs(len(x) - 4800) <= 1  # 0.1 s at 24 kHz -> 48 kHz


def test_gemini_falls_back_to_available_model(monkeypatch):
    calls = []
    monkeypatch.setattr(tts, "_gemini_model", "retired-tts")

    def call(model, *a):
        calls.append(model)
        return Resp(404, {"error": "not found"}) if model == "retired-tts" else Resp(200, audio_payload())

    monkeypatch.setattr(tts, "_gemini_call", call)
    monkeypatch.setattr(tts, "gemini_tts_models", lambda: ["new-flash-tts"])
    tts.synth_gemini("テスト", voice="Fenrir")
    assert calls == ["retired-tts", "new-flash-tts"] and tts.gemini_model_used() == "new-flash-tts"


def test_gemini_retries_rate_limit_then_succeeds(monkeypatch):
    seq = [Resp(429), Resp(200, audio_payload())]
    monkeypatch.setattr(tts, "_gemini_model", "m-tts")
    monkeypatch.setattr(tts, "_gemini_call", lambda *a: seq.pop(0))
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert len(tts.synth_gemini("テスト")) > 0


def test_gemini_402_tries_other_models_then_gives_up(monkeypatch):
    calls = []
    monkeypatch.setattr(tts, "_gemini_model", "paid-a-tts")
    monkeypatch.setattr(tts, "_gemini_tried", set())
    monkeypatch.setattr(tts, "gemini_tts_models", lambda: ["paid-a-tts", "paid-b-tts"])
    monkeypatch.setattr(tts, "_gemini_call", lambda m, *a: calls.append(m) or Resp(402))
    import pytest
    with pytest.raises(RuntimeError, match="402"):
        tts.synth_gemini("テスト")
    assert calls == ["paid-a-tts", "paid-b-tts"]


def test_gemini_402_falls_back_to_free_model(monkeypatch):
    monkeypatch.setattr(tts, "_gemini_model", "paid-tts")
    monkeypatch.setattr(tts, "_gemini_tried", set())
    monkeypatch.setattr(tts, "gemini_tts_models", lambda: ["paid-tts", "free-tts"])
    monkeypatch.setattr(tts, "_gemini_call", lambda m, *a: Resp(402) if m == "paid-tts" else Resp(200, audio_payload()))
    tts.synth_gemini("テスト")
    assert tts.gemini_model_used() == "free-tts"
