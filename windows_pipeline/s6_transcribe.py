"""LOOP step 6: transcribe the timeline with Resolve Studio's AI -> subtitle track.

PLAYBOOK 3.5: CreateSubtitlesFromAudio returns before the lines have finished
landing, so poll GetItemListInTrack until the count stops moving. The speech
model downloads once on first use, which is the slow part.
"""
import json
import time

from resolve_env import connect

STABLE_FOR = 6          # consecutive identical polls before we call it done
POLL = 10               # seconds
MAX_WAIT = 3600

resolve, project, tl = connect()

def line_count():
    n = 0
    for t in range(1, tl.GetTrackCount("subtitle") + 1):
        n += len(tl.GetItemListInTrack("subtitle", t) or [])
    return n

if tl.GetTrackCount("subtitle") == 0:
    print("no subtitle track — calling CreateSubtitlesFromAudio()", flush=True)
    ok = tl.CreateSubtitlesFromAudio()
    print("CreateSubtitlesFromAudio ->", ok, flush=True)
else:
    print(f"subtitle track already exists ({line_count()} lines) — not re-running",
          flush=True)

t0 = time.time()
last, same = -1, 0
while time.time() - t0 < MAX_WAIT:
    n = line_count()
    if n == last and n > 0:
        same += 1
        if same >= STABLE_FOR:
            break
    else:
        same = 0
        print(f"  t+{int(time.time()-t0):>4}s  lines={n}", flush=True)
    last = n
    time.sleep(POLL)

print(f"\nSTABLE at {last} subtitle lines after {int(time.time()-t0)}s "
      f"across {tl.GetTrackCount('subtitle')} track(s)", flush=True)

subs = sorted((i.GetStart(), i.GetEnd(), i.GetName())
              for t in range(1, tl.GetTrackCount("subtitle") + 1)
              for i in (tl.GetItemListInTrack("subtitle", t) or []))
json.dump([{"start": s, "end": e, "text": x} for s, e, x in subs],
          open("subs.json", "w"), indent=2)
print(f"wrote subs.json ({len(subs)} lines)")
if subs:
    print("first:", subs[0])
    print("last :", subs[-1])
print("SaveProject ->", resolve.GetProjectManager().SaveProject())
