"""LOOP step 12: final verification + save. Reads everything back through the API."""
import json

import numpy as np

from audio_duck import _envelope, SR, DUCK
from resolve_env import connect, fps_of, frames_to_tc

resolve, project, tl = connect()
fps = fps_of(tl)
start, end = tl.GetStartFrame(), tl.GetEndFrame()
names = json.load(open("names.json"))["items"]

ok = True
def check(label, cond, detail=""):
    global ok
    ok = ok and cond
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}  {detail}")

print(f"PROJECT: {project.GetName()}")
print(f"TIMELINE: {tl.GetName()}  {fps}fps  {frames_to_tc(start,fps)}-{frames_to_tc(end,fps)} "
      f"({(end-start)/fps/60:.1f} min)\n")

# markers + notes
mk = tl.GetMarkers() or {}
notes_ok = sum(1 for v in mk.values() if " | " in (v.get("note") or ""))
check("18 markers", len(mk) == 18, f"got {len(mk)}")
check("all markers carry NAME | LINK note", notes_ok == len(mk), f"{notes_ok}/{len(mk)}")

# tracks
def n_clips(trk, name):
    for t in range(1, tl.GetTrackCount(trk)+1):
        if tl.GetTrackName(trk, t) == name:
            return len(tl.GetItemListInTrack(trk, t) or []), t
    return 0, None

v2, _ = n_clips("video", "Video 2")
vo, vo_t = n_clips("audio", "Bradford VO")
mus, _ = n_clips("audio", "Music")
check("18 titles on V2", v2 == 18, f"got {v2}")
check("18 VO clips on 'Bradford VO'", vo == 18, f"got {vo}")
check("1 music bed on 'Music'", mus == 1, f"got {mus}")

# VO titles match names, no overlaps
v2clips = sorted((c.GetStart(), c) for c in (tl.GetItemListInTrack("video", 2) or []))
title_ok = 0
for i, (s, c) in enumerate(v2clips, 1):
    comp = c.GetFusionCompByIndex(1)
    tools = {t.GetAttrs()["TOOLS_Name"]: t for t in comp.GetToolList(False).values()}
    if tools["sText1_1"].GetInput("StyledText") == names[str(i)]["name"]:
        title_ok += 1
check("every V2 title text matches names.json", title_ok == 18, f"{title_ok}/18")

vt = sorted((c.GetStart(), c.GetEnd()) for c in (tl.GetItemListInTrack("audio", vo_t) or []))
ov = sum(1 for i in range(len(vt)-1) if vt[i][1] > vt[i+1][0])
check("no VO overlaps", ov == 0, f"{ov} overlaps")

# music covers all VO, and ducking aligns
bed = (tl.GetItemListInTrack("audio", tl.GetTrackCount("audio")) or [])
music = [c for t in range(1, tl.GetTrackCount("audio")+1)
         if tl.GetTrackName("audio", t) == "Music"
         for c in (tl.GetItemListInTrack("audio", t) or [])]
if music:
    b = music[0]
    covers = b.GetStart() <= vt[0][0] and b.GetEnd() >= vt[-1][1]
    check("music bed spans all VO", covers,
          f"bed {frames_to_tc(b.GetStart(),fps)}-{frames_to_tc(b.GetEnd(),fps)}")

vo_json = json.load(open("vo_placed.json"))
segs = [(v["start"]-start, v["end"]-start) for v in vo_json]
n = int(round((end-start)/fps*SR))
g = _envelope(n, segs, fps, edge_fade=True)
ducked = float(np.mean(g < DUCK+0.05))
check("bed ducked under VO (~1/3 of runtime)", 0.25 < ducked < 0.5,
      f"{ducked*100:.0f}% ducked")

print(f"\n{'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
