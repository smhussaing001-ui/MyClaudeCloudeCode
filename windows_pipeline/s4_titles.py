"""LOOP step 4: place the branded lower-third on V2, one per marker.

PLAYBOOK 3.3: AppendToTimeline with an explicit trackIndex + recordFrame is the
only reliable way to hit an exact track+frame (Insert*Title* ripples V1).
Title template = the 'Upper Thread' bin's Fusion Composition; tool names verified
by s0_inspect_titles.py: sText1_1 = name (top), sText1 = link (bottom).

Usage:  python s4_titles.py [items...]     e.g. python s4_titles.py 1
"""
import json
import sys

from resolve_env import connect, fps_of, frames_to_tc

TITLE_BIN = "Upper Thread"
DUR = 360                     # 12s @30fps; min marker gap is 1040f, so safe
HOLD = 1000

data = json.load(open("items.json"))
names = json.load(open("names.json"))["items"]
fps = data["fps"]
wanted = [int(a) for a in sys.argv[1:]]
items = [i for i in data["items"] if not wanted or i["n"] in wanted]

resolve, project, tl = connect()
mp = project.GetMediaPool()

fus = None
def walk(f):
    global fus
    for c in (f.GetClipList() or []):
        if f.GetName() == TITLE_BIN and c.GetClipProperty("Type") == "Fusion Composition":
            fus = c
    for s in (f.GetSubFolderList() or []):
        walk(s)
walk(mp.GetRootFolder())
if fus is None:
    raise SystemExit(f"No Fusion Composition found in bin {TITLE_BIN!r}")

while tl.GetTrackCount("video") < 2:
    tl.AddTrack("video")
    print(f"added video track -> V{tl.GetTrackCount('video')}")

for it in items:
    n, rec = it["n"], it["frame"]
    meta = names[str(n)]
    if it["len_frames"] < DUR:
        print(f"  {n:>2}  SKIP: span {it['len_frames']}f < title {DUR}f")
        continue
    ok = mp.AppendToTimeline([{ "mediaPoolItem": fus, "startFrame": 0,
        "endFrame": DUR - 1, "trackIndex": 2, "recordFrame": rec,
        "mediaType": 1 }])
    placed = [c for c in (tl.GetItemListInTrack("video", 2) or [])
              if c.GetStart() == rec]
    if not ok or not placed:
        print(f"  {n:>2}  APPEND FAILED (ok={ok})")
        continue
    clip = placed[0]
    comp = clip.GetFusionCompByIndex(1)
    if not comp:
        print(f"  {n:>2}  placed but comp NOT editable")
        continue
    tools = {t.GetAttrs()["TOOLS_Name"]: t for t in comp.GetToolList(False).values()}
    tools["sText1_1"].SetInput("StyledText", meta["name"])
    tools["sText1"].SetInput("StyledText", meta["link"])
    tools["MediaIn2"].SetInput("HoldLastFrame", HOLD)     # write-only, no read-back
    # read back from the API, not a screenshot
    got_n = tools["sText1_1"].GetInput("StyledText")
    got_l = tools["sText1"].GetInput("StyledText")
    print(f"  {n:>2}  V2 {frames_to_tc(clip.GetStart(), fps)} "
          f"f={clip.GetStart()}-{clip.GetEnd()} ({clip.GetEnd()-clip.GetStart()}f)  "
          f"name={got_n!r} link={got_l!r}  "
          f"{'OK' if (got_n == meta['name'] and got_l == meta['link']) else 'MISMATCH'}")

v2 = tl.GetItemListInTrack("video", 2) or []
print(f"\nV2 now holds {len(v2)} title clips | V1 untouched: "
      f"{len(tl.GetItemListInTrack('video', 1) or [])} clips")
