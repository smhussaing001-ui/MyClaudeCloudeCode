from resolve_env import connect
resolve, project, tl = connect()
for k in ("timelineResolutionWidth","timelineResolutionHeight","timelineFrameRate"):
    print(k, "=", tl.GetSetting(k))
print("proj setting:", project.GetSetting("timelineResolutionWidth"), "x",
      project.GetSetting("timelineResolutionHeight"))
print("V1 clips:", len(tl.GetItemListInTrack("video", 1) or []))
print("subtitle tracks:", tl.GetTrackCount("subtitle"))
