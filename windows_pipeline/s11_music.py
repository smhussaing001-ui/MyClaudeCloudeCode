"""LOOP step 11: build + place a VO-ducked music bed.

PLAYBOOK 3.9: Resolve can't duck via API, so audio_duck bakes a gain envelope
(-12 dB under every VO region) into a WAV. Verify by RE-DERIVING the envelope,
not a single-point RMS.

IMPORTANT coordinate note: this timeline starts at frame 108000 (01:00:00:00),
not 0. The bed must be built in timeline-RELATIVE frames (0 = timeline start) and
placed at recordFrame = start, or the envelope spans the wrong length.
"""
import glob
import json
import os
import random
import sys

import numpy as np

from audio_duck import build_bed, _decode, _envelope, SR, DUCK, FULL_GAIN
from resolve_env import connect, fps_of, clip_frames, frames_to_tc

BED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bed.wav")
TRACK = "Music"
BIN = "Music"

resolve, project, tl = connect()
fps = fps_of(tl)
start, end = tl.GetStartFrame(), tl.GetEndFrame()
total = end - start

mp = project.GetMediaPool()
def find(f, target):
    if f.GetName() == target:
        return f
    for s in (f.GetSubFolderList() or []):
        r = find(s, target)
        if r:
            return r
mbin = find(mp.GetRootFolder(), BIN)

# only real music files, not a previously-imported bed.wav
tracks = [c for c in (mbin.GetClipList() or [])
          if c.GetClipProperty("Type") == "Audio"
          and c.GetName().lower().endswith(".mp3")]
if not tracks:
    sys.exit("No mp3 tracks in the Music bin.")

pick = random.choice(tracks)
src = pick.GetClipProperty("File Path")
print(f"RANDOM pick: {pick.GetName()}  ({pick.GetClipProperty('Duration')})")
print(f"  {src}")

# --- VO regions -> timeline-relative frames ---
vo = json.load(open("vo_placed.json"))
segments = [(v["start"] - start, v["end"] - start) for v in vo]
print(f"\n{len(segments)} VO regions | timeline {total}f ({total/fps/60:.1f} min)")

# --- bake the bed ---
build_bed(src, BED, segments, total, fps)
print(f"wrote {os.path.basename(BED)}  {os.path.getsize(BED)/1e6:.1f} MB")

# --- VERIFY by re-deriving the envelope (PLAYBOOK: not a spot RMS) ---
n = int(round(total / fps * SR))
g = _envelope(n, segments, fps, edge_fade=True)
ducked = float(np.mean(g < (DUCK + 0.05)))         # fraction of samples at duck floor
full = float(np.mean(g > 0.95))
print(f"\nenvelope check: {ducked*100:.1f}% of bed ducked (~-12 dB), "
      f"{full*100:.1f}% at full. floor={g.min():.3f} peak={g.max():.3f}")
# spot-confirm three VO centres are ducked and three gaps are full
for i in (0, len(segments)//2, len(segments)-1):
    s0, s1 = segments[i]
    mid = int((s0 + s1) / 2 / fps * SR)
    print(f"  VO {vo[i]['name']}: gain@centre={g[mid]:.3f} "
          f"{'OK ducked' if g[mid] < DUCK + 0.02 else 'NOT DUCKED'}")

# --- import bed + place on a new Music track at recordFrame = start ---
mp.SetCurrentFolder(mbin)
before = {c.GetName() for c in (mbin.GetClipList() or [])}
mp.ImportMedia([BED])
bed_mpi = next(c for c in mbin.GetClipList() if c.GetName() not in before
               or c.GetName() == "bed.wav")

vtrk = None
for t in range(1, tl.GetTrackCount("audio") + 1):
    if tl.GetTrackName("audio", t) == TRACK:
        vtrk = t
if vtrk is None:
    tl.AddTrack("audio", "stereo")
    vtrk = tl.GetTrackCount("audio")
    tl.SetTrackName("audio", vtrk, TRACK)
    print(f"\nadded audio track A{vtrk} '{TRACK}'")

fr = clip_frames(bed_mpi, fps)
ok = mp.AppendToTimeline([{ "mediaPoolItem": bed_mpi, "startFrame": 0,
    "endFrame": fr - 1, "trackIndex": vtrk, "recordFrame": start,
    "mediaType": 2 }])
placed = tl.GetItemListInTrack("audio", vtrk) or []
print(f"placed bed ({fr}f) at {frames_to_tc(start, fps)} -> {ok} | "
      f"A{vtrk} has {len(placed)} clip(s), "
      f"covers {frames_to_tc(placed[0].GetStart(), fps)}"
      f"-{frames_to_tc(placed[0].GetEnd(), fps)}" if placed else "FAILED")
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
