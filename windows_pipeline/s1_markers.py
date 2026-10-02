"""LOOP step 1: connect + read markers -> items.json (abs frames + spans)."""
import json
from resolve_env import connect, fps_of, frames_to_tc

resolve, project, tl = connect()
fps = fps_of(tl)
start, end = tl.GetStartFrame(), tl.GetEndFrame()

mk = tl.GetMarkers() or {}                       # keys are OFFSETS from start
items = sorted((start + int(k), v) for k, v in mk.items())

out = []
for n, (frame, md) in enumerate(items, 1):
    span_end = items[n][0] if n < len(items) else end
    out.append({
        "n": n, "frame": frame, "tc": frames_to_tc(frame, fps),
        "span_end": span_end, "len_frames": span_end - frame,
        "len_s": round((span_end - frame) / fps, 1),
        "color": md.get("color"), "marker_name": md.get("name"),
        "note": md.get("note", ""),
    })

print(f"timeline={tl.GetName()} fps={fps} start={start} end={end} "
      f"({(end-start)/fps/60:.1f} min)")
print(f"markers={len(out)}")
for i in out:
    print(f"  {i['n']:>2}  {i['tc']}  f={i['frame']:<7} span={i['len_frames']:>5}f "
          f"({i['len_s']:>5}s)  {i['color']:<8} name={i['marker_name']!r} "
          f"note={i['note'][:60]!r}")

gaps = [i["len_frames"] for i in out]
print(f"\nMIN GAP between markers = {min(gaps)}f = {min(gaps)/fps:.1f}s "
      f"(title duration must stay under this)")

json.dump({"fps": fps, "start": start, "end": end, "items": out},
          open("items.json", "w"), indent=2)
print("wrote items.json")
