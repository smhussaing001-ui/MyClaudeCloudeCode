"""
audio_duck.py — bake a VO-ducked music bed with numpy (Resolve has NO scriptable
ducking / sidechain, so we print the gain envelope straight into a WAV).

Cross-platform. Needs: numpy, and ffmpeg on PATH (for mp3->wav decode).
    pip install numpy
    Windows ffmpeg: https://www.gyan.dev/ffmpeg/builds/  (add bin\\ to PATH)

Two entry points:
  build_bed(src, out, vo_segments, total_frames, fps)  -> one continuous bed
  build_segment(src, out, seg_len_frames, vo_in_seg, fps) -> one segment clip

vo_segments / vo_in_seg are lists of (start_frame, end_frame) in TIMELINE frames.
For build_segment they are RELATIVE to the segment start (0 = segment start).
"""
import subprocess
import wave
import numpy as np

SR = 48000
FULL_GAIN = 0.35          # music peak ~ -9 dBFS between VO
DUCK_DB = -12.0           # dip under narration
DUCK = 10 ** (DUCK_DB / 20.0)      # = 0.251
ATT, REL = 0.25, 0.45     # duck ramp down / up (seconds)
XF = 0.5                  # loop crossfade (seconds)
FADE = 0.6                # master / segment-edge fade (seconds)


def _decode(path):
    """mp3/wav/... -> float32 stereo numpy via ffmpeg piped raw s16le."""
    p = subprocess.run(
        ["ffmpeg", "-v", "quiet", "-i", path, "-ac", "2", "-ar", str(SR),
         "-f", "s16le", "-"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError(f"ffmpeg failed to decode {path}. Is ffmpeg on PATH?")
    x = np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return x.reshape(-1, 2)


def _loop_to(src, n):
    """Peak-normalise then loop src to exactly n samples with equal-power xfades."""
    src = src / (np.max(np.abs(src)) + 1e-9) * 0.98
    L = len(src); xf = int(XF * SR); out = np.zeros((n, 2), np.float32)
    fin = np.sqrt(np.linspace(0, 1, xf, dtype=np.float32)); fout = fin[::-1]
    pos, first = 0, True
    while pos < n:
        end = min(pos + L, n); chunk = src[:end - pos].copy()
        if not first and pos + xf <= n:
            out[pos:pos + xf] *= fout[:, None]
            k = min(xf, len(chunk)); chunk[:k] *= fin[:k, None]
        out[pos:end] += chunk; pos += L - xf; first = False
    return out


def _envelope(n, vo, fps, edge_fade=True):
    """Per-sample gain: 1.0 full, DUCK under each vo (start,end) in FRAMES,
    with attack/release ramps, plus optional fade-in/out at the ends."""
    g = np.ones(n, np.float32); a = int(ATT * SR); rl = int(REL * SR)
    for s0f, s1f in vo:
        s0 = int(s0f / fps * SR); s1 = int(s1f / fps * SR)
        g[max(0, s0):min(n, s1)] = DUCK
        if s0 - a >= 0:
            g[s0 - a:s0] = np.linspace(1, DUCK, a, dtype=np.float32)
        if s1 + rl <= n:
            g[s1:s1 + rl] = np.linspace(DUCK, 1, rl, dtype=np.float32)
    if edge_fade:
        fi = min(int(FADE * SR), n // 2)
        g[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
        g[-fi:] *= np.linspace(1, 0, fi, dtype=np.float32)
    return g


def _write(out, arr):
    np.clip(arr, -1, 1, arr)
    w = wave.open(out, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((arr * 32767).astype(np.int16).tobytes()); w.close()


def build_bed(src, out, vo_segments, total_frames, fps):
    """One continuous ducked bed the length of the whole timeline."""
    n = int(round(total_frames / fps * SR))
    mus = _loop_to(_decode(src), n)
    g = _envelope(n, vo_segments, fps, edge_fade=True)
    mus *= g[:, None] * FULL_GAIN
    _write(out, mus)


def build_segment(src, out, seg_len_frames, vo_in_seg, fps):
    """One ducked clip for a single segment (vo_in_seg is RELATIVE frames)."""
    n = int(round(seg_len_frames / fps * SR))
    mus = _loop_to(_decode(src), n)
    g = _envelope(n, vo_in_seg, fps, edge_fade=True)
    mus *= g[:, None] * FULL_GAIN
    _write(out, mus)
