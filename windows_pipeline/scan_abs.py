"""Scan caption strips at ABSOLUTE frames (not marker-relative).
Usage: python scan_abs.py <frame> <frame> ...
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from resolve_env import connect, fps_of, goto, frames_to_tc

CROP = (0, 40, 1250, 290)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stills", "scan")

frames = [int(a) for a in sys.argv[1:]]
resolve, project, tl = connect()
fps = fps_of(tl)
os.makedirs(OUT, exist_ok=True)
album = project.GetGallery().GetCurrentStillAlbum()
resolve.OpenPage("color")

strips = []
for f in frames:
    if not goto(tl, f, fps):
        print(f"  {f}: playhead failed to settle")
        continue
    still = tl.GrabStill()
    prefix = f"abs_{f}"
    album.ExportStills([still], OUT, prefix, "png")
    album.DeleteStills([still])
    hits = sorted(glob.glob(os.path.join(OUT, prefix + "*.png")))
    if not hits:
        print(f"  {f}: export failed")
        continue
    im = Image.open(hits[0]).crop(CROP)
    im = im.resize((im.width // 2, im.height // 2))
    strips.append((f, im))
    print(f"  f={f}  {frames_to_tc(f, fps)}  ok")

for drx in glob.glob(os.path.join(OUT, "*.drx")):
    os.remove(drx)

if strips:
    w = max(s.width for _, s in strips) + 190
    sheet = Image.new("RGB", (w, sum(s.height + 6 for _, s in strips)), "white")
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
    except OSError:
        font = ImageFont.load_default()
    d = ImageDraw.Draw(sheet)
    y = 0
    for f, s in strips:
        sheet.paste(s, (190, y))
        d.text((6, y + s.height // 2 - 14), frames_to_tc(f, fps), fill="black", font=font)
        d.line([(0, y + s.height + 3), (w, y + s.height + 3)], fill="black", width=2)
        y += s.height + 6
    out = os.path.join(OUT, "sheet_abs.png")
    sheet.save(out)
    print("wrote", out, sheet.size)
