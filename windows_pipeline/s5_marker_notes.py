"""LOOP step 5: write 'NAME | LINK' into each marker note.

PLAYBOOK 3.4: there is no marker-note setter. Delete + re-add IS the setter, so
every marker is read first, rebuilt, and verified before moving to the next one.
First line stays 'NAME | LINK' as a re-parseable contract; the rewritten script
gets appended below it in step 8.

Usage:  python s5_marker_notes.py [items...]
"""
import json
import sys

from resolve_env import connect, frames_to_tc

data = json.load(open("items.json"))
names = json.load(open("names.json"))["items"]
fps = data["fps"]
wanted = [int(a) for a in sys.argv[1:]]
items = [i for i in data["items"] if not wanted or i["n"] in wanted]

resolve, project, tl = connect()
start = tl.GetStartFrame()
fails = 0

for it in items:
    n, frame = it["n"], it["frame"]
    key = frame - start
    meta = names[str(n)]
    line = f"{meta['name']} | {meta['link']}"

    md = (tl.GetMarkers() or {}).get(key)
    if md is None:
        print(f"  {n:>2}  NO MARKER at offset {key} — skipped")
        fails += 1
        continue

    keep = (md["color"], md["name"], md.get("duration") or 1)
    note = md.get("note") or ""
    body = note.split("\n\n", 1)[1] if "\n\n" in note else ""
    newnote = f"{line}\n\n{body}" if body else line

    if not tl.DeleteMarkerAtFrame(key):
        print(f"  {n:>2}  DELETE FAILED — marker left intact")
        fails += 1
        continue
    ok = tl.AddMarker(key, keep[0], keep[1], newnote, keep[2])
    back = (tl.GetMarkers() or {}).get(key)
    if not ok or back is None:
        print(f"  {n:>2}  *** RE-ADD FAILED (ok={ok}) — MARKER LOST at {key} ***")
        fails += 1
        continue
    good = back.get("note", "").split("\n")[0] == line and back["name"] == keep[1]
    print(f"  {n:>2}  {frames_to_tc(frame, fps)}  {back['color']:<6} "
          f"{back['name']!r}  note[0]={back.get('note','').splitlines()[0]!r}  "
          f"{'OK' if good else 'MISMATCH'}")
    if not good:
        fails += 1

mk = tl.GetMarkers() or {}
print(f"\nmarkers on timeline={len(mk)} (expected {len(data['items'])}) | failures={fails}")
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
