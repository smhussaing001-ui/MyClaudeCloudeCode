"""Read the timeline back and draw it as text (no screenshots - PLAYBOOK rule 0.1)."""
import json
import os

from resolve_env import connect, fps_of, frames_to_tc

resolve, project, tl = connect()
fps = fps_of(tl)
start, end = tl.GetStartFrame(), tl.GetEndFrame()
data = json.load(open("items.json"))
names = json.load(open("names.json"))["items"]

mk = tl.GetMarkers() or {}
markers = sorted((start + int(k), v) for k, v in mk.items())
v2 = {c.GetStart(): c for c in (tl.GetItemListInTrack("video", 2) or [])}

print(f"TIMELINE {tl.GetName()}  {fps}fps  f{start}-{end}  "
      f"({(end-start)/fps/60:.1f} min)")
print(f"tracks: V={tl.GetTrackCount('video')} A={tl.GetTrackCount('audio')} "
      f"S={tl.GetTrackCount('subtitle')}")
for t in range(1, tl.GetTrackCount("video") + 1):
    print(f"  V{t} '{tl.GetTrackName('video', t)}': "
          f"{len(tl.GetItemListInTrack('video', t) or [])} clips")
for t in range(1, tl.GetTrackCount("audio") + 1):
    print(f"  A{t} '{tl.GetTrackName('audio', t)}': "
          f"{len(tl.GetItemListInTrack('audio', t) or [])} clips")

print(f"\n{'#':>3} {'marker TC':<12} {'span':>7} {'V2 title':<20} {'title text':<38} vo")
for idx, (frame, md) in enumerate(markers):
    n = idx + 1
    nxt = markers[idx + 1][0] if idx + 1 < len(markers) else end
    clip = v2.get(frame)
    if clip:
        comp = clip.GetFusionCompByIndex(1)
        tools = {t.GetAttrs()["TOOLS_Name"]: t for t in comp.GetToolList(False).values()}
        txt = tools["sText1_1"].GetInput("StyledText")
        cell = f"f{clip.GetStart()}+{clip.GetEnd()-clip.GetStart()}"
    else:
        txt, cell = "-", "MISSING"
    vo = "yes" if os.path.exists(f"vo/clip_{n:02d}.mp3") else "-"
    print(f"{n:>3} {frames_to_tc(frame, fps):<12} {(nxt-frame)/fps:>6.1f}s "
          f"{cell:<20} {txt[:37]:<38} {vo}")

# proportional map
W = 96
print(f"\nmap ({W} cols = {(end-start)/fps/60:.1f} min)")
row = ["."] * W
for idx, (frame, _) in enumerate(markers):
    col = int((frame - start) / (end - start) * (W - 1))
    row[col] = str((idx + 1) % 10)
print("V1 |" + "=" * W + "|")
print("MK |" + "".join(row) + "|")
t2 = ["."] * W
for s, c in v2.items():
    a = int((s - start) / (end - start) * (W - 1))
    b = max(a, int((c.GetEnd() - start) / (end - start) * (W - 1)))
    for i in range(a, b + 1):
        t2[i] = "#"
print("V2 |" + "".join(t2) + "|")
print("   |" + frames_to_tc(start, fps) + " " * (W - 22) + frames_to_tc(end, fps) + "|")
