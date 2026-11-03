"""Synthesizes every soundtrack from the collision events: soft SFX in front, a barely-there pad behind."""
import json
import wave
from pathlib import Path

import numpy as np

SR = 48000
DUR = 20.0
N = int(SR * DUR)
ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "audio-build"
OUT = ROOT / "public" / "audio"
OUT.mkdir(parents=True, exist_ok=True)

# Pad level: quiet enough to sit under the SFX as air rather than as a tune.
PAD_LEVEL = 0.018


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def modal(freq, ratios, amps, decays, dur, attack=0.004):
    """A struck resonator. The rounded attack is what keeps every hit soft, never clicky."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    s = np.zeros(n)
    for r, a, d in zip(ratios, amps, decays):
        f = freq * r
        if f < SR * 0.42:
            s += a * np.sin(2 * np.pi * f * t) * np.exp(-t / d)
    s *= np.minimum(1.0, t / attack) ** 2
    fade = int(0.02 * SR)
    s[-fade:] *= np.linspace(1, 0, fade)
    return s


def place(buf, sig, t, gain=1.0, pan=0.0):
    start = int(t * SR)
    if start >= len(buf):
        return
    end = min(len(buf), start + len(sig))
    a = (pan + 1) * np.pi / 4
    buf[start:end, 0] += sig[: end - start] * gain * np.cos(a)
    buf[start:end, 1] += sig[: end - start] * gain * np.sin(a)


def spectral(x, lo, hi):
    """Gentle band-limit in the frequency domain."""
    X = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(x.shape[0], 1 / SR)
    g = 1.0 / np.sqrt(1 + (f / hi) ** 4)
    g *= 1.0 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)
    if x.ndim == 2:
        g = g[:, None]
    return np.fft.irfft(X * g, n=x.shape[0], axis=0)


def reverb(dry, seed, seconds=2.4, wet=0.26, bright=4200):
    """Convolution with synthetic decaying noise: a soft, large room."""
    rs = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rs.standard_normal((n, 2)) * np.exp(-t * 6.9 / seconds)[:, None]
    ir[: int(0.012 * SR)] = 0
    ir = spectral(ir, 180, bright)
    ir /= np.sqrt((ir**2).sum(axis=0))
    L = dry.shape[0] + n
    w = np.fft.irfft(np.fft.rfft(dry, L, axis=0) * np.fft.rfft(ir, L, axis=0), L, axis=0)[: dry.shape[0]]
    return dry + wet * w


def pad(chords, seed):
    """Chords: list of (start, [midi...]). Slow sine swells only, no rhythm."""
    out = np.zeros((N, 2))
    t = np.arange(N) / SR
    rs = np.random.default_rng(seed)
    for k, (t0, notes) in enumerate(chords):
        t1 = chords[k + 1][0] if k + 1 < len(chords) else DUR + 1
        env = np.clip((t - t0) / 2.2, 0, 1) * np.clip((t1 + 1.5 - t) / 2.5, 0, 1)
        env = env * env * (3 - 2 * env)
        for m in notes:
            for ch, det in enumerate((0.998, 1.002)):
                ph = rs.uniform(0, 6.28)
                wob = 1 + 0.25 * np.sin(2 * np.pi * rs.uniform(0.05, 0.13) * t + ph)
                out[:, ch] += np.sin(2 * np.pi * midi(m) * det * t + ph) * env * wob
    out /= max(1e-9, np.abs(out).max())
    master = np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)
    return out * master[:, None] * PAD_LEVEL


def rain(density_times, gains, seed, lo=1400, hi=6500, smooth_s=0.35, level=0.05):
    """A patter bed whose loudness follows how many collisions are happening."""
    rs = np.random.default_rng(seed)
    noise = spectral(rs.standard_normal((N, 2)), lo, hi)
    noise /= np.abs(noise).max()
    env = np.zeros(N)
    for t, g in zip(density_times, gains):
        i = int(t * SR)
        if i < N:
            env[i] += g
    kernel = np.hanning(int(smooth_s * SR))
    env = np.convolve(env, kernel / kernel.sum(), mode="same")
    env /= max(1e-9, env.max())
    return noise * env[:, None] * level


def finish(name, sfx, music, seed):
    sfx = reverb(sfx, seed)
    # Normalise the SFX alone so the pad's level stays fixed beneath them.
    sfx *= 0.62 / max(1e-9, np.abs(sfx).max())
    mix = sfx + music
    t = np.arange(N) / SR
    mix *= (np.clip(t / 0.02, 0, 1) * np.clip((DUR - t) / 0.5, 0, 1))[:, None]
    mix = np.tanh(mix * 1.1) / 1.1
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(OUT / f"{name}.raw.wav"), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(name, "sfx rms %.4f  music rms %.4f" % (np.sqrt((sfx**2).mean()), np.sqrt((music**2).mean())))


def load(name):
    return json.loads((EV / f"{name}.json").read_text())


def cradle():
    sfx = np.zeros((N, 2))
    rs = np.random.default_rng(1)
    # A rounded wood-and-steel knock, pitched by how many balls are swinging.
    base = {1: midi(74), 2: midi(69), 3: midi(62)}
    for e in load("cradle"):
        f = base[e["i"]] * rs.uniform(0.997, 1.003)
        s = modal(f, [1, 2.71, 5.2], [1, 0.28, 0.07], [0.2, 0.07, 0.025], 0.9, attack=0.003)
        place(sfx, s, e["t"], 0.3 + 0.7 * e["v"], (-1) ** round(e["t"] / 0.75) * 0.22)
    return "cradle", sfx, pad([(0, [50, 57, 66]), (6.6, [45, 52, 61]), (13.2, [50, 57, 62])], 1), 1


def ring():
    sfx = np.zeros((N, 2))
    # Pentatonic arpeggio climbing in phrases, so the chaos still sounds composed.
    scale = [57, 60, 62, 64, 67, 69, 72, 74, 76, 79, 81]
    walk = [0, 2, 4, 3, 5, 7, 6, 8, 10, 7, 5, 3]
    evs = load("ring")
    last = -1.0
    for k, e in enumerate(evs):
        if e["t"] - last < 0.07:
            continue
        last = e["t"]
        m = scale[walk[k % len(walk)]]
        s = modal(midi(m), [1, 3.01, 6.2], [1, 0.16, 0.035], [0.75, 0.2, 0.06], 2.2, attack=0.005)
        pan = (e["x"] - 540) / 440 * 0.55
        place(sfx, s, e["t"], 0.28 + 0.4 * e["v"], pan)
    return "ring", sfx, pad([(0, [45, 52, 60]), (7, [41, 48, 57]), (14, [45, 52, 59])], 2), 2


def pi():
    sfx = np.zeros((N, 2))
    rs = np.random.default_rng(3)
    last = -1.0
    for e in load("pi"):
        # Dense bursts are thinned to a soft purr rather than a harsh buzz.
        gap = 0.036
        if e["t"] - last < gap:
            continue
        last = e["t"]
        rise = np.sin(np.pi * e["frac"])
        base = (340 + 520 * rise) if e["run"] == 1 else (400 + 480 * rise)
        wall = e["kind"] == "wall"
        s = modal(base * (0.78 if wall else 1.0) * rs.uniform(0.985, 1.015), [1, 2.4, 4.3], [1, 0.22, 0.05], [0.075, 0.03, 0.012], 0.3, attack=0.002)
        gain = 0.36 if e["run"] == 0 else 0.25
        place(sfx, s, e["t"], gain * (0.75 + 0.25 * rs.random()), -0.3 if wall else 0.05)
    # A small bell answers each result.
    for t, notes in ((4.45, [72, 79]), (16.45, [72, 79, 84])):
        for j, m in enumerate(notes):
            place(sfx, modal(midi(m), [1, 2.76, 5.1], [1, 0.14, 0.03], [1.3, 0.3, 0.09], 3.2, attack=0.006), t + j * 0.13, 0.5)
    return "pi", sfx, pad([(0, [48, 55, 64]), (6.5, [45, 52, 60]), (15.5, [48, 55, 64])], 3), 3


def galton():
    sfx = np.zeros((N, 2))
    rs = np.random.default_rng(4)
    evs = load("galton")
    scale = [76, 78, 80, 83, 85, 88, 90, 92, 95, 97]
    last = -1.0
    # Audible drops are capped near 24 per second; the rest become the rain bed.
    for e in (x for x in evs if x["kind"] == "peg"):
        if e["t"] - last < 0.042:
            continue
        last = e["t"]
        f = midi(scale[e["i"]]) * rs.uniform(0.996, 1.004)
        s = modal(f, [1, 2.2], [1, 0.1], [0.13, 0.04], 0.45, attack=0.004)
        place(sfx, s, e["t"], 0.09 + 0.07 * rs.random(), (e["x"] - 540) / 400 * 0.7)
    last = -1.0
    for e in (x for x in evs if x["kind"] == "land"):
        if e["t"] - last < 0.07:
            continue
        last = e["t"]
        s = modal(rs.uniform(190, 260), [1, 2.1], [1, 0.15], [0.07, 0.03], 0.25, attack=0.006)
        place(sfx, s, e["t"], 0.26, (e["x"] - 540) / 400 * 0.7)
    pegs = [x for x in evs if x["kind"] == "peg"]
    bed = rain([x["t"] for x in pegs], [1.0] * len(pegs), 40)
    place(sfx, modal(midi(64), [1, 3.0, 5.1], [1, 0.12, 0.03], [1.5, 0.4, 0.1], 3.0, attack=0.01), 18.0, 0.4)
    place(sfx, modal(midi(71), [1, 3.0, 5.1], [1, 0.12, 0.03], [1.5, 0.4, 0.1], 2.0, attack=0.01), 18.25, 0.3)
    return "galton", sfx + bed, pad([(0, [40, 47, 56]), (9, [37, 44, 52]), (15, [40, 47, 56])], 4), 4


def xylo():
    sfx = np.zeros((N, 2))
    top = [67, 69, 71, 74, 76, 79, 81, 83]
    bass = [48, 50, 52, 55, 57]
    for e in load("xylo"):
        if e["kind"] == "top":
            s = modal(midi(top[e["i"]]), [1, 3.92, 9.2], [1, 0.13, 0.025], [1.05, 0.2, 0.06], 2.8, attack=0.004)
            place(sfx, s, e["t"], 0.56 * e["v"], (e["i"] - 3.5) / 3.5 * 0.45)
        else:
            s = modal(midi(bass[e["i"]]), [1, 2.0, 3.9], [1, 0.26, 0.06], [1.5, 0.55, 0.12], 3.2, attack=0.008)
            place(sfx, s, e["t"], 0.5 * e["v"], (e["i"] - 2) / 2 * 0.3)
    return "xylo", sfx, pad([(0, [43, 50, 59]), (5, [40, 47, 55]), (10, [36, 43, 52]), (15, [43, 50, 59])], 5), 5


if __name__ == "__main__":
    for build in (cradle, ring, pi, galton, xylo):
        finish(*build())
