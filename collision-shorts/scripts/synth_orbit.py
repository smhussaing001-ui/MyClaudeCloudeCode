"""Soundtracks for the orbit geometry series: a soft chime per orbit, a deeper bell when worlds meet."""
import numpy as np

from synth_audio import DUR, N, SR, finish, load, midi, modal, pad, place, spectral


def sheen(seed, level=0.012):
    """A faint airy swell that grows with the drawing and fades after it."""
    rs = np.random.default_rng(seed)
    x = spectral(rs.standard_normal((N, 2)), 900, 5200)
    x /= np.abs(x).max()
    t = np.arange(N) / SR
    env = np.clip((t - 1) / 15, 0, 1) ** 1.5 * np.clip((18.6 - t) / 1.6, 0, 1)
    return x * env[:, None] * level


def bell(m, decay=1.5):
    return modal(midi(m), [1, 2.76, 5.4], [1, 0.13, 0.03], [decay, 0.35, 0.09], decay * 2.4, attack=0.006)


def weave(name, scale_a, scale_b, meet, chords, seed):
    sfx = np.zeros((N, 2))
    for e in load(name):
        if e["kind"] == "a":
            place(sfx, bell(scale_a[e["i"] % len(scale_a)], 1.0), e["t"], 0.32, -0.35)
        elif e["kind"] == "b":
            place(sfx, bell(scale_b[e["i"] % len(scale_b)], 1.1), e["t"], 0.36, 0.35)
        else:
            place(sfx, bell(meet[e["i"] % len(meet)], 2.4), e["t"], 0.7, 0.0)
    return name, sfx + sheen(seed), pad(chords, seed), seed


def venus():
    return weave("weave-venus", [79, 81, 83, 86, 88], [67, 71, 74], [55, 62, 59, 64, 55], [(0, [43, 50, 59]), (9, [40, 47, 55]), (15, [43, 50, 59])], 21)


def saturn():
    return weave("weave-saturn", [72, 74, 79], [67, 60], [48, 55, 48], [(0, [36, 43, 52]), (10, [41, 48, 57])], 22)


def mars():
    return weave("weave-mars", [81, 84, 86, 88, 91], [69, 72, 74, 76], [57, 64, 60, 62, 57, 64, 57], [(0, [45, 52, 60]), (8, [41, 48, 57]), (14, [45, 52, 60])], 23)


def geo():
    sfx = np.zeros((N, 2))
    orbit = [86, 88, 91, 93, 91, 88]
    loop = [62, 67, 69, 74, 62]
    for e in load("geo"):
        if e["kind"] == "orbit":
            place(sfx, bell(orbit[e["i"] % len(orbit)], 0.9), e["t"], 0.24, 0.3 * np.sin(e["i"]))
        else:
            place(sfx, bell(loop[e["i"] % len(loop)], 2.2), e["t"], 0.72, 0.0)
    return "geo", sfx + sheen(24), pad([(0, [38, 45, 54]), (10, [43, 50, 59])], 24), 24


def rose():
    sfx = np.zeros((N, 2))
    # A slow rising and falling scale: one note for each close pass of the Sun.
    scale = [69, 71, 74, 76, 78, 81, 83, 86, 88, 86, 83, 81, 78, 76, 74, 71]
    for e in load("rose"):
        place(sfx, bell(scale[e["i"] % len(scale)], 1.2), e["t"], 0.48, 0.45 * np.sin(e["i"] * 0.26))
    place(sfx, bell(57, 2.6), 17.1, 0.65, 0.0)
    return "rose", sfx + sheen(25), pad([(0, [45, 52, 61]), (10, [42, 49, 57])], 25), 25


if __name__ == "__main__":
    for build in (venus, saturn, mars, geo, rose):
        finish(*build())
    print("duration", DUR)
