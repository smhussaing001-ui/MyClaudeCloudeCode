"""Soundtracks for the solar system series, in the same soft style as synth_audio.py."""
import numpy as np

from synth_audio import N, SR, finish, load, midi, modal, pad, place, spectral


def bode():
    sfx = np.zeros((N, 2))
    # Falling pentatonic: each world further out rings lower.
    notes = [91, 88, 86, 83, 81, 79, 76, 74, 67]
    for e in load("bode"):
        m = notes[e["i"]]
        s = modal(midi(m), [1, 2.76, 5.4], [1, 0.14, 0.03], [1.5, 0.35, 0.09], 3.4, attack=0.006)
        place(sfx, s, e["t"], 0.65, 0.45 * np.sin(e["i"] * 0.82))
    return "bode", sfx, pad([(0, [43, 50, 59]), (9, [40, 47, 55]), (17.5, [38, 45, 53])], 11), 11


def laplace():
    sfx = np.zeros((N, 2))
    # Octaves plus a fifth: the 4:2:1 rhythm made audible.
    notes = [(81, -0.3), (74, 0.3), (62, 0.0)]
    for e in load("laplace"):
        m, pan = notes[e["i"]]
        decay = [0.75, 1.0, 1.5][e["i"]]
        s = modal(midi(m), [1, 3.9, 8.8], [1, 0.11, 0.02], [decay, 0.18, 0.05], 3.0, attack=0.005)
        place(sfx, s, e["t"], [0.42, 0.5, 0.72][e["i"]], pan)
    return "laplace", sfx, pad([(0, [38, 45, 54])], 12), 12


def asteroid():
    sfx = np.zeros((N, 2))
    rs = np.random.default_rng(13)
    for e in load("asteroid"):
        k = e["i"]
        # Pitch drops half an octave per doubling; loudness barely grows so it stays gentle.
        f = 620 / 2 ** (k * 0.5)
        s = modal(f, [1, 1.9, 3.4, 5.6], [1, 0.42, 0.14, 0.05], [0.18 + k * 0.1, 0.11 + k * 0.04, 0.05, 0.02], 2.5, attack=0.012)
        place(sfx, s, e["t"], 0.5 + k * 0.04, 0.0)
        # A hush of settling dust instead of a blast.
        n = int(SR * (0.9 + k * 0.16))
        dust = spectral(rs.standard_normal((n, 2)), 300, 2600 - k * 220)
        env = np.minimum(1, np.arange(n) / (0.03 * SR)) * np.exp(-np.arange(n) / (0.2 * SR + k * 0.04 * SR))
        dust = dust * env[:, None]
        dust /= np.abs(dust).max()
        start = int(e["t"] * SR)
        end = min(N, start + n)
        sfx[start:end] += dust[: end - start] * 0.09
    return "asteroid", sfx, pad([(0, [36, 43, 52]), (10, [33, 40, 48])], 13), 13


def accretion():
    sfx = np.zeros((N, 2))
    rs = np.random.default_rng(14)
    # Each round is a step lower: bodies are bigger, so they ring deeper.
    notes = [93, 88, 81, 76, 69, 57]
    gains = [0.2, 0.26, 0.34, 0.44, 0.58, 0.85]
    for e in load("accretion"):
        r = e["i"]
        s = modal(midi(notes[r]) * rs.uniform(0.997, 1.003), [1, 2.7, 5.2], [1, 0.13, 0.03], [0.55 + r * 0.25, 0.18, 0.05], 3.2, attack=0.005)
        place(sfx, s, e["t"], gains[r], e["x"] * 0.6)
    return "accretion", sfx, pad([(0, [41, 48, 57]), (8, [38, 45, 53]), (15, [41, 48, 57])], 14), 14


def bounce():
    sfx = np.zeros((N, 2))
    for e in load("bounce"):
        # Gets quieter and slightly higher as the bounces shrink, like the real thing.
        k = e["i"]
        s = modal(midi(64 + k * 0.5), [1, 2.8, 5.3], [1, 0.16, 0.04], [0.5, 0.12, 0.03], 2.0, attack=0.004)
        place(sfx, s, e["t"], max(0.1, e["v"] ** 0.75) * 0.8, 0.08)
    return "bounce", sfx, pad([(0, [40, 47, 56])], 15), 15


if __name__ == "__main__":
    for build in (bode, laplace, asteroid, accretion, bounce):
        finish(*build())
