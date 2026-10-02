# DaVinci Resolve Auto-Edit Playbook (for Claude Code)

You are automating a **Top-N machinery listicle** edit in **DaVinci Resolve
Studio** through its Python scripting API. A human places one **marker** at the
start of each list item; you do everything else: grab a still per item, read the
on-screen machine name + link, drop a branded title, transcribe + rewrite the
narration, generate a voiceover, and lay a **ducked** music bed.

This file is the distilled result of a long trial-and-error session. **Only the
approaches that actually worked are here.** The "DEAD ENDS" section lists what to
never try again — respect it; each one cost real time to disprove.

Two ready-made modules ship next to this file — import them, don't rewrite them:
`resolve_env.py` (cross-platform connect + shared helpers) and `audio_duck.py`
(the numpy ducking renderer).

---

## 0. Golden rules (read first)

1. **API text over screenshots.** Verify everything by *reading the timeline
   back through the API* (clip starts, ends, names, marker notes). Screenshots
   and full-res still reads are the single biggest token cost — avoid them. When
   you must read a frame, crop the top caption band and downscale (~13× cheaper).
2. **Verify after every write.** Place → read back → confirm → only then move on.
   Several silent failures in this pipeline only surfaced on read-back.
3. **`SaveProject()` is on ProjectManager, not Project.** (`resolve_env.save()`.)
4. **Never trust a grabbed frame without a settle + timecode read-back** — the
   playhead lags and you capture a stale frame. Use `resolve_env.goto()`.
5. **Audio clips have no `Frames` property** — only `Duration` as `HH:MM:SS:FF`.
   Use `resolve_env.clip_frames()`.
6. **Placement is `MediaPool.AppendToTimeline` with an explicit `trackIndex` +
   `recordFrame`.** This is the ONLY reliable way to hit an exact track+frame.

---

## 1. Environment (Windows)

* DaVinci Resolve **Studio** (free version can't auto-caption), running, with the
  project + timeline open.
* Resolve **Preferences > System > General > External scripting using = Local**.
* **Python 3.10+ 64-bit.**  `pip install numpy requests`
* **ffmpeg** on PATH (for mp3→wav in the music step): gyan.dev build, add `bin\`.
* Sanity check:
  ```bash
  python -c "from resolve_env import connect; print(connect()[1].GetName())"
  ```
  Prints the project name = you're wired up. If it errors, follow the header of
  `resolve_env.py` and set `RESOLVE_SCRIPT_API` / `RESOLVE_SCRIPT_LIB`.

---

## 2. The per-video LOOP

Run these in order for each new video. Each step is idempotent-ish and verified
by read-back. `>>>` = a script you write (patterns below); modules do the heavy
lifting.

```
FOR EACH VIDEO:
  1. connect + read markers            -> list of (abs_frame, name)
  2. grab a still per marker           -> item_NN.png + cropped strip_NN.png
  3. [YOU read the strips]             -> per item: NAME + LINK   (caps, verbatim)
  4. place a title per marker on V2    -> branded lower-third, text + hold set
  5. write NAME|LINK into marker note  -> survives outside this session
  6. transcribe timeline (Studio AI)   -> subtitle track
  7. slice dialogue by markers         -> dialogue.json  (+ ALIGN, see 8)
  8. [YOU rewrite each item's script]  -> reference tone, numbers spelled out
  9. generate VO (ElevenLabs)          -> clip_NN.mp3 per item
 10. place VO on a new audio track     -> at each marker, collision-safe
 11. build + place a ducked music bed  -> numpy, under the VO
 12. save project + verify counts
```

Steps 3 and 8 are *your* judgement (vision + writing). Everything else is
mechanical and scriptable. Do them in this order — **stills BEFORE titles**, or
the titles cover the baked captions you need to read.

---

## 3. Step-by-step (correct approaches)

### 3.1 Markers → items
```python
from resolve_env import connect, fps_of, frames_to_tc
resolve, project, tl = connect(); fps = fps_of(tl); start = tl.GetStartFrame()
mk = tl.GetMarkers() or {}                      # keys are OFFSETS from start
items = sorted((start + int(k), v) for k, v in mk.items())   # -> abs frames
```
Item N spans from marker N up to (not including) marker N+1; the last runs to
`tl.GetEndFrame()`.

### 3.2 Stills per marker  (settle + one-file-per-prefix + crop)
* Move with `goto()` (settle + read-back) or you get **stale duplicate frames**.
* Grab on the **Color** page: `resolve.OpenPage("color")`, `tl.GrabStill()`.
* **Export ONE still at a time under a per-item prefix.** A batch
  `ExportStills([...])` names files `s_1.1`, `s_1.10`, `s_1.2` … and a
  lexicographic sort maps image→item WRONG. Per-item prefix kills the ambiguity.
* Crop the **top caption band** (`(0, 40, ~1250, 290)`) and downscale ~50%; read
  THOSE, batched into a contact sheet, not the 6 MB frames.
* Clean up the `.drx` grade files Resolve drops next to each PNG.
* If `ExportStills` starts returning `False` mid-session (a known Resolve state
  glitch — not disk space), fall back to reading the **viewer** via a single
  screenshot; restarting Resolve clears it.

### 3.3 Titles on V2  (the big win — no ripple, editable, exact track)
Keep your branded title as a **"Fusion Composition"** clip in a Media Pool bin
(drag your Text+/Fusion title there once). Then:
```python
mp = project.GetMediaPool()
fus = <that Fusion Composition media-pool item>
mp.AppendToTimeline([{ "mediaPoolItem": fus, "startFrame": 0,
    "endFrame": DUR-1, "trackIndex": 2, "recordFrame": marker_abs_frame,
    "mediaType": 1 }])                          # mediaType 1 = video
item = <the new V2 clip at recordFrame>
comp = item.GetFusionCompByIndex(1)             # WORKS -> editable
tools = {t.GetAttrs()["TOOLS_Name"]: t for t in comp.GetToolList(False).values()}
tools["sText1_1"].SetInput("StyledText", NAME)  # Text Box 1 = name  (top)
tools["sText1"].SetInput("StyledText", LINK)    # Text Box 2 = link  (bottom)
tools["MediaIn2"].SetInput("HoldLastFrame", 1000)   # hold; macro input is write-only
```
`DUR` sets duration directly (no dialog). Check the **minimum gap between
markers** first so a 12s (288f @24fps) title can't overlap the next one.

> Tool names (`sText1_1`, `sText1`, `MediaIn2`) are specific to that template.
> Inspect once: dump `comp.GetToolList(False)` and each tool's `TOOLS_Name` /
> its inputs' `INPS_Name` to find "name", "link", "hold" on YOUR title, then
> hard-code them like above.

### 3.4 Marker notes (there is no setter)
```python
key = marker_abs_frame - start
md = (tl.GetMarkers())[key]
tl.DeleteMarkerAtFrame(key)
tl.AddMarker(key, md["color"], md["name"], f"{NAME} | {LINK}\n\n{script}",
             md["duration"] or 1)               # delete + re-add = the "setter"
```
Keep `NAME | LINK` as the first line — it's a stable contract you can re-parse.

### 3.5 Transcribe + slice
```python
if tl.GetTrackCount("subtitle") == 0:
    tl.CreateSubtitlesFromAudio()               # Studio only; model downloads once
    # poll GetItemListInTrack("subtitle",1) until the line count is STABLE
subs = sorted((i.GetStart(), i.GetEnd(), i.GetName())
              for t in range(1, tl.GetTrackCount("subtitle")+1)
              for i in (tl.GetItemListInTrack("subtitle", t) or []))
```
Slice each item = subs whose start is in `[marker_N, marker_N+1)`. **Then ALIGN:**
markers sit where the on-screen title appears, which *lags* the narrator naming
the machine by ~20–85 frames. Snap each item's start back to the earliest
subtitle line (within ~20s) that first mentions a distinctive word of the item
name — it lifts name-match accuracy and stops sentences being cut mid-word.

### 3.6 Script rewrite (tone)
Per item: **name → the PROBLEM it solves → how it works → the numbers.** Calm
third person, no hype; connectives like "It's noteworthy that", "The advantages
include", "Unlike other X on our list". Budget ~80–90 words/item.
**For TTS: spell numbers/model codes out** ("EX eight thousand dash six", "R
nine thousand eight hundred") or the voice mangles alphanumerics. Fix ASR typos
(brand names especially). Never invent specs — drop a garbled number rather than
guess.

### 3.7 Voiceover (ElevenLabs)  — key from ENV, never hard-coded
```python
import os, requests
key = os.environ["ELEVENLABS_API_KEY"]          # set it in the shell, don't paste
r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
    headers={"xi-api-key": key, "Content-Type": "application/json"},
    json={"text": script, "model_id": "eleven_multilingual_v2",
          "voice_settings": {"stability":0.5,"similarity_boost":0.75,
                             "style":0.0,"use_speaker_boost":True}}, timeout=180)
open(f"clip_{n:02d}.mp3","wb").write(r.content)  # 200 = ok; JSON body = error
```
Generate ONE test item first and confirm the numbers read right before the batch.

### 3.8 Place VO
Add a dedicated audio track, then append each clip. **Anchor to the marker
frame**; if a clip would collide with the previous one, push it to
`prev_end + gap`.
```python
tl.AddTrack("audio", "stereo"); vtrk = tl.GetTrackCount("audio")
tl.SetTrackName("audio", vtrk, "Howard VO")
fr = clip_frames(vo_mpi, fps)                    # audio -> Duration TC, not Frames
mp.AppendToTimeline([{ "mediaPoolItem": vo_mpi, "startFrame":0, "endFrame":fr-1,
    "trackIndex": vtrk, "recordFrame": anchor, "mediaType": 2 }])  # 2 = audio
```

### 3.9 Ducked music  (Resolve can't duck via API — bake it)
Read every VO clip's `(start,end)` off the VO track(s). Then:
```python
from audio_duck import build_bed          # or build_segment for per-segment music
build_bed("track.mp3", "bed.wav", vo_segments, tl.GetEndFrame(), fps)
# import bed.wav, AppendToTimeline onto a new "Music" audio track at recordFrame 0
```
`audio_duck` peak-normalises, loops with equal-power crossfades, and prints a
gain envelope that dips **−12 dB under every VO region** (0.25s/0.45s ramps) with
2s/4s fades. Verify by re-deriving the envelope, NOT by single-point RMS (the
song's own dynamics fool a spot check).
**If the VO later moves, the baked duck won't follow — re-render the bed.**

---

## 4. DEAD ENDS — do not attempt (already disproven)

* **`InsertFusionTitleIntoTimeline` / `InsertTitleIntoTimeline`** — always land
  on V1 and *ripple* the base footage sideways. No track targeting. Use §3.3.
* **`CreateFusionClip` to make a placeable title** — the resulting "Fusion Clip"
  has `GetFusionCompCount()==0`: NOT editable. Only a "Fusion Composition"
  media-pool item stays editable after `AppendToTimeline`.
* **Locking / disabling V1 to redirect an insert** — it just refuses; no redirect.
* **Epidemic Sound via API or your login token** — the token from the website is
  a web-session token; the Partner API rejects it (401), and there's no MCP
  connector. Music: the human downloads tracks (Epidemic app / DaVinci's built-in
  extension) into a Media Pool bin; you read the file paths and duck them.
* **`osascript` keystrokes** — macOS-only and blocked without Accessibility; on
  Windows irrelevant. Drive UI (if unavoidable) with the platform's own tools.
* **Batch `ExportStills`** for identity-critical stills — lexicographic filename
  sort scrambles image→item. One export per item, per-item prefix.
* **Reordering clips in place** — there is no move-clip API. To reorder segments,
  BUILD A NEW TIMELINE and `AppendToTimeline` the pieces in the new order; when
  the source fps ≠ timeline fps, convert every boundary by the frame ratio
  (`source_frame = round(timeline_frame * src_total / timeline_total)`).
* **Screenshot-heavy verification** — burns tokens. Read the timeline via API.

---

## 5. Kickoff

Give your Windows Claude the sibling `KICKOFF.md` as its first message (or paste
its contents). It points here and starts the loop on the currently-open project.
