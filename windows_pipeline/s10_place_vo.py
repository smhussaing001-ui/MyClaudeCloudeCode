"""LOOP step 10: import the VO clips and lay them on a new audio track.

PLAYBOOK 3.8: dedicated audio track; anchor each clip to its MARKER frame; if a
clip would collide with the previous one, push it to prev_end + gap. Audio clips
have no 'Frames' property, so length comes from clip_frames() (Duration TC).
AppendToTimeline with mediaType 2 + explicit trackIndex + recordFrame is the only
reliable exact placement.
"""
import glob
import json
import os

from resolve_env import connect, fps_of, clip_frames, frames_to_tc

BIN = "Bradford VO"
TRACK = "Bradford VO"
GAP = 15                     # 0.5s @30fps min space if two clips would collide
VO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vo")

data = json.load(open("items.json"))
fps = data["fps"]
items = data["items"]

resolve, project, tl = connect()
mp = project.GetMediaPool()
root = mp.GetRootFolder()

# --- import the clips into a dedicated bin (idempotent-ish: reuse existing) ---
bin_ = next((s for s in (root.GetSubFolderList() or []) if s.GetName() == BIN), None)
if bin_ is None:
    bin_ = mp.AddSubFolder(root, BIN)
mp.SetCurrentFolder(bin_)
have = {c.GetName(): c for c in (bin_.GetClipList() or [])}
paths = [p for p in sorted(glob.glob(os.path.join(VO_DIR, "clip_*.mp3")))
         if os.path.basename(p) not in have]
if paths:
    mp.ImportMedia(paths)
vo = {c.GetName(): c for c in (bin_.GetClipList() or [])}
print(f"VO bin holds {len(vo)} clips")

# --- add the track (only if not already there) ---
vtrk = None
for t in range(1, tl.GetTrackCount("audio") + 1):
    if tl.GetTrackName("audio", t) == TRACK:
        vtrk = t
if vtrk is None:
    tl.AddTrack("audio", "stereo")
    vtrk = tl.GetTrackCount("audio")
    tl.SetTrackName("audio", vtrk, TRACK)
    print(f"added audio track A{vtrk} '{TRACK}'")
else:
    print(f"reusing audio track A{vtrk} '{TRACK}'")

existing = tl.GetItemListInTrack("audio", vtrk) or []
if existing:
    print(f"  track already has {len(existing)} clips — leaving them; "
          "delete the track in Resolve to re-place cleanly.")

# --- place each clip ---
prev_end = 0
placed = 0
print(f"\n{'#':>3} {'marker':>9} {'anchor':>9} {'len':>6} {'end':>9} {'push':>6}")
for it in items:
    n = it["n"]
    name = f"clip_{n:02d}.mp3"
    mpi = vo.get(name)
    if mpi is None:
        print(f"{n:>3}  MISSING {name}")
        continue
    fr = clip_frames(mpi, fps)
    anchor = it["frame"]
    push = ""
    if anchor < prev_end + GAP:
        anchor = prev_end + GAP
        push = "PUSHED"
    ok = mp.AppendToTimeline([{ "mediaPoolItem": mpi, "startFrame": 0,
        "endFrame": fr - 1, "trackIndex": vtrk, "recordFrame": anchor,
        "mediaType": 2 }])
    end = anchor + fr
    print(f"{n:>3} {frames_to_tc(it['frame'], fps)} {frames_to_tc(anchor, fps)} "
          f"{fr:>5}f {frames_to_tc(end, fps)} {push:>6}  {'OK' if ok else 'FAIL'}")
    if ok:
        placed += 1
        prev_end = end

# --- read back ---
track = sorted((c.GetStart(), c.GetEnd(), c.GetName())
               for c in (tl.GetItemListInTrack("audio", vtrk) or []))
print(f"\nplaced {placed}/{len(items)} | track A{vtrk} now has {len(track)} clips")
overlap = [(track[i][2], track[i+1][2]) for i in range(len(track)-1)
           if track[i][1] > track[i+1][0]]
print("overlaps:", overlap or "none")
json.dump([{"start": s, "end": e, "name": nm} for s, e, nm in track],
          open("vo_placed.json", "w"), indent=2)
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
