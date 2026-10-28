"""Procedural BGM + SFX and the final mix. Everything here is generated from code,
so there are no third-party music licensing questions."""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000
rng = np.random.default_rng(1234)


def _t(dur):
    return np.arange(int(dur * SR)) / SR


def _ts(n):
    return np.arange(n) / SR


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, n=len(x)).astype(np.float32)


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / (1 + (f / hi) ** 4) * (1 - 1 / (1 + (f / lo) ** 4))
    return np.fft.irfft(X, n=len(x)).astype(np.float32)


def env_adsr(n, a=0.005, d=0.1, s=0.6, r=0.2):
    e = np.ones(n, dtype=np.float32) * s
    na, nd, nr = int(a * SR), int(d * SR), int(r * SR)
    na, nd = min(na, n), min(nd, max(0, n - na))
    e[:na] = np.linspace(0, 1, na)
    e[na:na + nd] = np.linspace(1, s, nd)
    if nr and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------- SFX
def sfx_whoosh(dur=0.6):
    n = int(dur * SR)
    noise = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32)
    steps = 12
    for i in range(steps):
        a, b = i * n // steps, (i + 1) * n // steps
        f = 300 * (12 ** (i / steps))
        out[a:b] = bandpass(noise, f * 0.6, f * 1.6)[a:b]
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * e * 0.5


def sfx_impact(dur=1.4):
    t = _t(dur)
    f = 110 * np.exp(-t * 5) + 38
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.8)
    crack = lowpass(rng.standard_normal(len(t)).astype(np.float32), 2500) * np.exp(-t * 18)
    return (body * 0.9 + crack * 0.5).astype(np.float32)


def sfx_ding(dur=0.9, note=88):
    t = _t(dur)
    x = sum(np.sin(2 * np.pi * midi(note) * h * t) / h ** 1.6 for h in (1, 2.01, 3.02, 4.2))
    return (x * np.exp(-t * 5) * 0.35).astype(np.float32)


def sfx_tick(dur=0.06):
    t = _t(dur)
    return (np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 90) * 0.25).astype(np.float32)


def sfx_riser(dur=2.0):
    t = _t(dur)
    f = 200 * (8 ** (t / dur))
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15
    noise = bandpass(rng.standard_normal(len(t)).astype(np.float32), 800, 6000) * 0.25
    return ((tone + noise) * (t / dur) ** 2).astype(np.float32)


def sfx_rumble(dur=2.5):
    t = _t(dur)
    x = lowpass(rng.standard_normal(len(t)).astype(np.float32), 120) * 2.5
    return (x * np.sin(np.linspace(0, np.pi, len(t)))).astype(np.float32)


SFX = {"whoosh": sfx_whoosh, "impact": sfx_impact, "ding": sfx_ding, "tick": sfx_tick, "riser": sfx_riser,
       "rumble": sfx_rumble}


# ---------------------------------------------------------------- BGM
def bgm(total: float, bpm: float = 112, climax: float | None = None, mood: str = "epic") -> np.ndarray:
    """Pulsing cinematic loop in A minor (Am-F-C-G), intensity rising toward `climax`."""
    n = int(total * SR)
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]
    bar = beat * 4
    climax = climax or total * 0.7

    def intensity(tt):
        return float(np.clip(0.35 + 0.65 * (tt / climax), 0.35, 1.0)) if tt < climax else 1.0

    t_bar = 0.0
    i = 0
    while t_bar < total:
        root, chord = prog[i % 4]
        L = min(bar, total - t_bar)
        tt = _t(L)
        a = int(t_bar * SR)
        inten = intensity(t_bar)
        # pad: detuned saws, low-passed
        pad = np.zeros(len(tt), np.float32)
        for m in chord:
            for det in (-0.08, 0.08):
                ph = (midi(m + 12) * (1 + det / 100) * tt) % 1.0
                pad += (2 * ph - 1) * 0.05
        pad = lowpass(pad, 900 + 1800 * inten) * env_adsr(len(tt), 0.3, 0.5, 0.8, 0.3)
        # sub bass on 8ths
        bass = np.zeros(len(tt), np.float32)
        for k in range(8):
            s = int(k * beat / 2 * SR)
            if s >= len(tt):
                break
            m = int(min(len(tt) - s, beat / 2 * SR))
            tb = _ts(m)
            bass[s:s + m] += np.sin(2 * np.pi * midi(root - 12) * tb) * env_adsr(m, 0.005, 0.12, 0.5, 0.05) * 0.35
        # kick on each beat, hats on offbeats once intensity rises
        drums = np.zeros(len(tt), np.float32)
        for k in range(4):
            s = int(k * beat * SR)
            if s >= len(tt):
                break
            m = min(len(tt) - s, int(0.35 * SR))
            tk = _ts(m)
            drums[s:s + m] += np.sin(2 * np.pi * (45 + 120 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 9) * 0.6
            if inten > 0.55:
                s2 = s + int(beat / 2 * SR)
                if s2 < len(tt):
                    m2 = min(len(tt) - s2, int(0.05 * SR))
                    hat = bandpass(rng.standard_normal(m2 + 64).astype(np.float32), 6000, 14000)[:m2]
                    drums[s2:s2 + m2] += hat * np.exp(-_ts(m2) * 60) * 0.25 * inten
        # arpeggio (16ths) after 40% intensity
        arp = np.zeros(len(tt), np.float32)
        if inten > 0.45:
            notes = [chord[0] + 24, chord[1] + 24, chord[2] + 24, chord[1] + 24]
            for k in range(16):
                s = int(k * beat / 4 * SR)
                if s >= len(tt):
                    break
                m = min(len(tt) - s, int(beat / 4 * SR))
                ta = _ts(m)
                ph = (midi(notes[k % 4]) * ta) % 1.0
                arp[s:s + m] += (np.abs(2 * ph - 1) * 2 - 1) * np.exp(-ta * 14) * 0.07 * inten
        seg_mix = pad * (0.6 + 0.4 * inten) + bass * inten + drums * (0.5 + 0.5 * inten) + arp
        out[a:a + len(tt)] += seg_mix[: n - a]
        t_bar += bar
        i += 1
    fade = int(1.2 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)
    out[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    return out


# ---------------------------------------------------------------- mix
def place(buf: np.ndarray, x: np.ndarray, at: float, gain: float = 1.0):
    s = int(at * SR)
    if s >= len(buf):
        return
    m = min(len(x), len(buf) - s)
    buf[s:s + m] += x[:m] * gain


def mix(total: float, voice_events, sfx_events, bpm=112, climax=None, bgm_gain=0.32, duck=0.45) -> np.ndarray:
    """voice_events: [(start_sec, samples)], sfx_events: [(start_sec, name, gain)]. Returns stereo float32."""
    n = int(total * SR)
    voice = np.zeros(n, np.float32)
    for at, x in voice_events:
        place(voice, x, at)
    fx = np.zeros(n, np.float32)
    for at, name, g in sfx_events:
        place(fx, SFX[name](), at, g)
    music = bgm(total, bpm=bpm, climax=climax)
    # sidechain-style ducking from voice envelope
    envv = np.abs(voice)
    win = int(0.12 * SR)
    envv = np.convolve(envv, np.ones(win) / win, mode="same")
    duck_env = 1 - duck * np.clip(envv / 0.08, 0, 1)
    out = voice * 1.0 + music * bgm_gain * duck_env + fx * 0.8
    peak = float(np.max(np.abs(out))) or 1.0
    out = out / peak * 0.95
    return np.stack([out, out], axis=1).astype(np.float32)


def write_wav(path: Path, stereo: np.ndarray):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
