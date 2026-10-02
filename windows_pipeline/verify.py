import json
from resolve_env import connect, fps_of, frames_to_tc
resolve, project, tl = connect()
fps = fps_of(tl)
data = json.load(open("items.json"))
print(f"end frame now={tl.GetEndFrame()}  (items.json recorded {data['end']})")
print(f"start now={tl.GetStartFrame()}  (recorded {data['start']})")
mk = tl.GetMarkers() or {}
now = sorted(tl.GetStartFrame() + int(k) for k in mk)
was = [i["frame"] for i in data["items"]]
print(f"markers now={len(now)} recorded={len(was)}  identical={now == was}")
if now != was:
    print("  now:", now); print("  was:", was)
v1 = tl.GetItemListInTrack("video", 1) or []
print(f"\nV1 clips={len(v1)}")
for c in v1:
    print(f"  f={c.GetStart():<7}-{c.GetEnd():<7} {frames_to_tc(c.GetStart(), fps)} {c.GetName()[:52]}")
