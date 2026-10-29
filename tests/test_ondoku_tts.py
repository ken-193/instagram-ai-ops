import pytest

from pipeline import tts


class Resp:
    def __init__(self, status, payload=None, content=b""):
        self.status_code, self._p, self.content = status, payload, content
        self.text = str(payload)

    def json(self):
        if self._p is None:
            raise ValueError("not json")
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(tts, "ondoku_chars_used", 0)
    monkeypatch.setattr("time.sleep", lambda s: None)


def test_ondoku_success_downloads_and_decodes(monkeypatch):
    sent = []
    monkeypatch.setattr(tts, "_ondoku_call", lambda body: sent.append(body) or Resp(200, {"url": "https://x/a.mp3"}))
    monkeypatch.setattr("requests.get", lambda url, timeout: Resp(200, None, b"MP3"))
    monkeypatch.setattr(tts, "_decode_audio", lambda b: __import__("numpy").ones(4800, dtype="float32"))
    x = tts.synth_ondoku("月までの距離", voice="en-HK-SamNeural", speed=1.1)
    assert len(x) == 4800
    assert sent[0] == {"pitch": 0.0, "speed": 1.1, "text": "月までの距離", "voice": "en-HK-SamNeural"}
    assert tts.ondoku_chars_used == len("月までの距離")


def test_ondoku_quota_notice_audio_is_never_used(monkeypatch):
    monkeypatch.setattr(tts, "_ondoku_call", lambda body: Resp(200, {"code": "quota_exceeded", "available": 12,
                                                                     "url": "https://x/notice.mp3"}))
    monkeypatch.setattr("requests.get", lambda *a, **k: pytest.fail("notice audio must not be downloaded"))
    with pytest.raises(tts.OndokuQuotaError):
        tts.synth_ondoku("テスト")


def test_ondoku_http_error_and_missing_url(monkeypatch):
    monkeypatch.setattr(tts, "_ondoku_call", lambda body: Resp(400, {"error": "この音声では本文を読み上げできませんでした"}))
    with pytest.raises(RuntimeError, match="400.*読み上げできません"):
        tts.synth_ondoku("テスト")
    monkeypatch.setattr(tts, "_ondoku_call", lambda body: Resp(200, {"message": "ng"}))
    with pytest.raises(RuntimeError):
        tts.synth_ondoku("テスト")


def test_ondoku_retries_server_errors(monkeypatch):
    seq = [Resp(503, None), Resp(200, {"url": "https://x/a.mp3"})]
    monkeypatch.setattr(tts, "_ondoku_call", lambda body: seq.pop(0))
    monkeypatch.setattr("requests.get", lambda url, timeout: Resp(200, None, b"MP3"))
    monkeypatch.setattr(tts, "_decode_audio", lambda b: __import__("numpy").ones(10, dtype="float32"))
    assert len(tts.synth_ondoku("テスト")) == 10


def test_decode_audio_with_ffmpeg():
    import subprocess
    wav = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=f=440:d=0.5", "-f", "mp3", "pipe:1"],
                         capture_output=True).stdout
    x = tts._decode_audio(wav)
    assert 0.45 * tts.SR < len(x) < 0.6 * tts.SR


def test_voice_candidates_are_complete():
    from pipeline.voice_samples import VOICES
    for name, c in VOICES.items():
        assert c["backend"] in ("ondoku", "gemini", "openjtalk") and c["voice"] and c["label"], name
    assert VOICES["Sam"]["voice"] == "en-HK-SamNeural"
