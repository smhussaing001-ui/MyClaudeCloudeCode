"""Diagnostic: scan one item at several offsets to find when its caption is up.
Usage: python scan.py <item_n> <off1> <off2> ...
"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from resolve_env import connect, fps_of, goto, frames_to_tc

CROP = (0, 40, 1250, 290)
# NOTE: ExportStills returns False for a RELATIVE folder path. Must be absolute.
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stills", "scan")

n = int(sys.argv[1])
offsets = [int(a) for a in sys.argv[2:]]
data = json.load(open("items.json"))
fps = data["fps"]
it = next(i for i in data["items"] if i["n"] == n)

resolve, project, tl = connect()
os.makedirs(OUT, exist_ok=True)
album = project.GetGallery().GetCurrentStillAlbum()
resolve.OpenPage("color")

strips = []
for off in offsets:
    f = it["frame"] + off
    if f >= it["span_end"]:
        print(f"  +{off}: past span end, skipped")
        continue
    if not goto(tl, f, fps):
        print(f"  +{off}: playhead failed to settle")
        continue
    still = tl.GrabStill()
    prefix = f"scan_{n:02d}_{off:04d}"
    album.ExportStills([still], OUT, prefix, "png")
    album.DeleteStills([still])
    hits = sorted(glob.glob(os.path.join(OUT, prefix + "*.png")))
    if not hits:
        print(f"  +{off}: export failed")
        continue
    im = Image.open(hits[0]).crop(CROP)
    im = im.resize((im.width // 2, im.height // 2))
    strips.append((off, f, im))
    print(f"  +{off:>4}  {frames_to_tc(f, fps)}  ok")

for drx in glob.glob(os.path.join(OUT, "*.drx")):
    os.remove(drx)

if strips:
    w = max(s.width for _, _, s in strips) + 120
    sheet = Image.new("RGB", (w, sum(s.height + 6 for _, _, s in strips)), "white")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    y = 0
    for off, f, s in strips:
        sheet.paste(s, (120, y))
        d.text((8, y + s.height // 2 - 16), f"+{off}", fill="black", font=font)
        d.line([(0, y + s.height + 3), (w, y + s.height + 3)], fill="black", width=2)
        y += s.height + 6
    out = os.path.join(OUT, f"sheet_item{n:02d}.png")
    sheet.save(out)
    print("wrote", out, sheet.size)
