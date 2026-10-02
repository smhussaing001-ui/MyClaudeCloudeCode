"""LOOP step 2: grab a still per marker -> stills/item_NN.png + strip_NN.png

Per PLAYBOOK 3.2: settle+read-back before every grab (or you get stale frames),
ONE ExportStills call per item under a per-item prefix (batch export scrambles
image->item ordering lexicographically), crop the top caption band, drop the
.drx grade files Resolve leaves behind.

Usage:  python s2_stills.py [items...]      e.g. python s2_stills.py 1
        python s2_stills.py                 -> all items in items.json
"""
import glob
import json
import os
import sys

from PIL import Image

from resolve_env import connect, fps_of, goto, frames_to_tc

OFFSET = 60          # frames after the marker: let the title finish animating in
if "--offset" in sys.argv:                     # some sources animate in slower
    _i = sys.argv.index("--offset")
    OFFSET = int(sys.argv[_i + 1])
    del sys.argv[_i:_i + 2]
CROP = (0, 40, 1250, 290)      # top caption band @1920x1080
SCALE = 0.5
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stills")

data = json.load(open("items.json"))
fps = data["fps"]
wanted = [int(a) for a in sys.argv[1:]]
items = [i for i in data["items"] if not wanted or i["n"] in wanted]

resolve, project, tl = connect()
os.makedirs(OUT, exist_ok=True)
album = project.GetGallery().GetCurrentStillAlbum()
resolve.OpenPage("color")

for it in items:
    n, frame = it["n"], it["frame"] + OFFSET
    if not goto(tl, frame, fps):
        print(f"  {n:>2}  FAILED to settle playhead at {frames_to_tc(frame, fps)}")
        continue
    still = tl.GrabStill()
    if not still:
        print(f"  {n:>2}  GrabStill returned nothing")
        continue
    prefix = f"item_{n:02d}"
    # clear any prior export for this prefix, else a re-run's new file gets a
    # suffix (item_02_1.2.1.png) and sorted()[0] picks the STALE item_02.png
    for old in glob.glob(os.path.join(OUT, prefix + "*.png")):
        os.remove(old)
    ok = album.ExportStills([still], OUT, prefix, "png")
    album.DeleteStills([still])          # keep the gallery clean between runs
    hits = sorted(glob.glob(os.path.join(OUT, prefix + "*.png")))
    if not ok or not hits:
        print(f"  {n:>2}  ExportStills failed (ok={ok})")
        continue
    png = hits[0]
    final = os.path.join(OUT, f"item_{n:02d}.png")
    if png != final:
        os.replace(png, final)
    im = Image.open(final)
    strip = im.crop(CROP)
    strip = strip.resize((int(strip.width * SCALE), int(strip.height * SCALE)))
    strip.save(os.path.join(OUT, f"strip_{n:02d}.png"))
    print(f"  {n:>2}  {frames_to_tc(frame, fps)}  tc_readback={tl.GetCurrentTimecode()}"
          f"  {im.size}  -> strip {strip.size}")

for drx in glob.glob(os.path.join(OUT, "*.drx")):
    os.remove(drx)
print("cleaned .drx |", len(glob.glob(os.path.join(OUT, 'item_*.png'))), "stills on disk")
