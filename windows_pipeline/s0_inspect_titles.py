"""One-off probe: which Fusion Composition is the name/link lower-third, and what
are its real tool names?

PLAYBOOK 3.3 note: a Fusion Composition's comp is only reachable AFTER it is
placed on a timeline. So this builds a THROWAWAY timeline, places each candidate,
dumps the tool list, then deletes the timeline and restores Timeline 1.
Timeline 1 is never written to.
"""
from resolve_env import connect

PROBE = "ZZ_title_probe"
DUR = 300

resolve, project, tl_orig = connect()
mp = project.GetMediaPool()
root = mp.GetRootFolder()

cands = []
def walk(f):
    for c in (f.GetClipList() or []):
        if c.GetClipProperty("Type") == "Fusion Composition":
            cands.append((f.GetName(), c))
    for s in (f.GetSubFolderList() or []):
        walk(s)
walk(root)
print("candidates:", [b for b, _ in cands])

for t in (project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1)):
    if t.GetName() == PROBE:
        mp.DeleteTimelines([t])

probe = mp.CreateEmptyTimeline(PROBE)
project.SetCurrentTimeline(probe)
start = probe.GetStartFrame()

for idx, (binname, item) in enumerate(cands):
    rec = start + idx * (DUR + 30)
    ok = mp.AppendToTimeline([{ "mediaPoolItem": item, "startFrame": 0,
        "endFrame": DUR - 1, "trackIndex": 1, "recordFrame": rec,
        "mediaType": 1 }])
    placed = [c for c in (probe.GetItemListInTrack("video", 1) or [])
              if c.GetStart() == rec]
    print(f"\n=== [{idx}] bin={binname!r} append={bool(ok)} placed={len(placed)}")
    if not placed:
        continue
    comp = placed[0].GetFusionCompByIndex(1)
    if not comp:
        print("    NO editable comp")
        continue
    for tool in (comp.GetToolList(False) or {}).values():
        attrs = tool.GetAttrs()
        name = attrs.get("TOOLS_Name")
        kind = attrs.get("TOOLS_RegID")
        extra = ""
        if kind in ("TextPlus", "Text3D"):
            try:
                extra = f"  StyledText={tool.GetInput('StyledText')!r}"
            except Exception:
                pass
        print(f"    {name:<22} {kind}{extra}")

project.SetCurrentTimeline(tl_orig)
mp.DeleteTimelines([probe])
print(f"\nprobe timeline deleted | current timeline restored to "
      f"{project.GetCurrentTimeline().GetName()!r} | "
      f"timelines now={project.GetTimelineCount()}")
