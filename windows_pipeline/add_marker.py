"""Add one marker at an absolute frame, with a NAME | LINK note.
Usage: python add_marker.py <abs_frame> "NAME" "LINK" "Marker label"
"""
import sys

from resolve_env import connect, frames_to_tc, fps_of

frame = int(sys.argv[1])
name, link, label = sys.argv[2], sys.argv[3], sys.argv[4]

resolve, project, tl = connect()
fps = fps_of(tl)
start = tl.GetStartFrame()
key = frame - start

existing = tl.GetMarkers() or {}
if key in existing:
    sys.exit(f"A marker already exists at offset {key} ({frames_to_tc(frame, fps)}).")

ok = tl.AddMarker(key, "Blue", label, f"{name} | {link}", 1)
back = (tl.GetMarkers() or {}).get(key)
print(f"AddMarker @ {frames_to_tc(frame, fps)} (offset {key}) -> {ok}")
if back:
    print(f"  read back: name={back['name']!r} note={back['note']!r}")
print(f"markers now: {len(tl.GetMarkers() or {})}")
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
