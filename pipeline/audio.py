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


def sfx_splash(dur=1.2):
    t = _t(dur)
    noise = rng.standard_normal(len(t)).astype(np.float32)
    body = lowpass(noise, 1800) * np.exp(-t * 3.5)
    hiss = bandpass(noise, 2500, 9000) * np.exp(-t * 6) * 0.5
    return ((body + hiss) * np.clip(t / 0.02, 0, 1) * 0.8).astype(np.float32)


def sfx_boom(dur=3.5):
    t = _t(dur)
    f = 70 * np.exp(-t * 2) + 28
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.4)
    roar = lowpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 1.1) * 1.4
    spray = bandpass(rng.standard_normal(len(t)).astype(np.float32), 2000, 10000) * np.exp(-t * 1.8) * 0.5
    return ((sub + roar + spray) * 0.8).astype(np.float32)


SFX = {"splash": sfx_splash, "boom": sfx_boom, "whoosh": sfx_whoosh, "impact": sfx_impact, "ding": sfx_ding, "tick": sfx_tick, "riser": sfx_riser,
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


# ---------------------------------------------------------------- festival band (Awa-odori style, original)
def _taiko(dur=0.6):
    t = _t(dur)
    f = 62 + 70 * np.exp(-t * 28)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    skin = lowpass(rng.standard_normal(len(t)).astype(np.float32), 900) * np.exp(-t * 40) * 0.6
    return (body + skin).astype(np.float32)


def _shime(dur=0.12):
    t = _t(dur)
    tone = np.sin(2 * np.pi * 520 * t) * np.exp(-t * 45)
    snap = bandpass(rng.standard_normal(len(t)).astype(np.float32), 1500, 6000) * np.exp(-t * 80)
    return (tone * 0.6 + snap * 0.8).astype(np.float32)


def _kane(dur=0.35):
    t = _t(dur)
    x = sum(np.sin(2 * np.pi * 1180 * r * t) / (i + 1) for i, r in enumerate((1.0, 2.76, 5.4, 8.93)))
    hiss = bandpass(rng.standard_normal(len(t)).astype(np.float32), 5000, 12000) * np.exp(-t * 40) * 0.4
    return ((x * 0.35 + hiss) * np.exp(-t * 14)).astype(np.float32)


def _fue(freq, dur):
    t = _t(dur)
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.6 * t) * np.clip(t / 0.25, 0, 1)
    ph = np.cumsum(freq * vib) / SR
    tone = np.sin(2 * np.pi * ph) + 0.25 * np.sin(4 * np.pi * ph) + 0.08 * np.sin(6 * np.pi * ph)
    breath = bandpass(rng.standard_normal(len(t)).astype(np.float32), freq * 0.8, freq * 3) * 0.12
    return ((tone + breath) * env_adsr(len(t), 0.03, 0.08, 0.8, 0.05) * 0.22).astype(np.float32)


# own 8-bar phrase on the minyo (D F G A C) scale; (midi note, length in eighths)
FUE_PHRASE = [(81, 2), (84, 1), (81, 1), (79, 2), (77, 2), (79, 1), (81, 1), (79, 1), (77, 1), (74, 4),
              (77, 2), (79, 1), (81, 1), (84, 2), (86, 2), (84, 1), (81, 1), (79, 1), (81, 1), (74, 4)]


def matsuri(total: float, bpm: float = 128) -> tuple[np.ndarray, np.ndarray]:
    """Two-beat festival groove: big taiko, shime-daiko, kane (bell) + a shinobue-like flute line.
    Returns (percussion, flute)."""
    n = int(total * SR)
    perc = np.zeros(n, np.float32)
    flute = np.zeros(n, np.float32)
    six = 60 / bpm / 4
    taiko, shime, kane = _taiko(), _shime(), _kane()
    k = 0
    while k * six < total:
        pos = k % 8   # one 2/4 bar = 8 sixteenths
        at = k * six
        if pos in (0, 3, 4, 6):
            place(perc, taiko, at, 0.9 if pos in (0, 4) else 0.55)
        if pos % 2 == 0 or pos == 7:
            place(perc, shime, at, 0.35 if pos % 2 == 0 else 0.2)
        if pos in (0, 4):
            place(perc, kane, at, 0.3)
        elif pos in (2, 6):
            place(perc, kane, at, 0.14)
        k += 1
    at = 0.0
    while at < total:
        for note, ln in FUE_PHRASE:
            d = ln * six * 2
            place(flute, _fue(midi(note), d * 0.95), at)
            at += d
            if at >= total:
                break
    return perc, flute


# ---------------------------------------------------------------- mix
def place(buf: np.ndarray, x: np.ndarray, at: float, gain: float = 1.0):
    s = int(at * SR)
    if s >= len(buf):
        return
    m = min(len(x), len(buf) - s)
    buf[s:s + m] += x[:m] * gain


def _ramp(n, a: float, b: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.clip((t - a) / max(b - a, 0.01), 0, 1).astype(np.float32)


def mix(total: float, voice_events, sfx_events, bpm=112, climax=None, bgm_gain=0.32, duck=0.45,
        matsuri_from: float | None = None, matsuri_full: float | None = None, stems: bool = False,
        music_env: list[tuple[float, float]] | None = None):
    """voice_events: [(start_sec, samples)], sfx_events: [(start_sec, name, gain)]. Returns stereo float32
    (and {"voice", "music_sfx"} stems when stems=True).
    matsuri_from/full: the festival band fades in from far away (low-passed) at `matsuri_from` and takes
    over from the cinematic loop by `matsuri_full`."""
    n = int(total * SR)
    voice = np.zeros(n, np.float32)
    for at, x in voice_events:
        place(voice, x, at)
    fx = np.zeros(n, np.float32)
    for at, name, g in sfx_events:
        place(fx, SFX[name](), at, g)
    music = bgm(total, bpm=bpm, climax=climax)
    if matsuri_from is not None:
        full = matsuri_full if matsuri_full is not None else matsuri_from + 10
        perc, flute = matsuri(total, bpm)
        near = _ramp(n, matsuri_from + (full - matsuri_from) * 0.25, full)
        far = _ramp(n, matsuri_from, matsuri_from + 1.5) * (1 - near)
        band = lowpass(perc, 350) * 1.6 * far + perc * near + flute * _ramp(n, full - 1.0, full + 0.5)
        fade = int(1.2 * SR)
        band[-fade:] *= np.linspace(1, 0, fade)
        music = music * (1 - 0.8 * near) + band * 1.1
    if music_env:  # scripted music level: [(time, gain)], linear in between (e.g. a silence before a hit)
        pts = sorted(music_env)
        music = music * np.interp(np.arange(n) / SR, [p[0] for p in pts], [p[1] for p in pts]).astype(np.float32)
    # sidechain-style ducking from voice envelope
    envv = np.abs(voice)
    win = int(0.12 * SR)
    envv = np.convolve(envv, np.ones(win) / win, mode="same")
    duck_env = 1 - duck * np.clip(envv / 0.08, 0, 1)
    bed = music * bgm_gain * duck_env + fx * 0.8
    out = voice * 1.0 + bed
    peak = float(np.max(np.abs(out))) or 1.0
    g = 0.95 / peak
    stereo = np.stack([out * g, out * g], axis=1).astype(np.float32)
    if not stems:
        return stereo
    return stereo, {"voice": np.stack([voice * g] * 2, axis=1).astype(np.float32),
                    "music_sfx": np.stack([bed * g] * 2, axis=1).astype(np.float32)}


def write_wav(path: Path, stereo: np.ndarray):
    pcm = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
