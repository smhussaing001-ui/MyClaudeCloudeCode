"""Create the Anton captions in red and black, then build the final video.

    python finish.py            frames_v3 + vo.mp3 + timing.json -> crane_short_v3.mp4 + .srt
    python finish.py --test FRAME.jpg t     one caption test still at time t, to preview/
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FPS, TEMPO = 30, 1.1
W, H = 1080, 1920
ANTON = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts\Anton-Regular.ttf")
BIG = ImageFont.truetype(ANTON, 104)
SMALL = ImageFont.truetype(ANTON, 58)
ORANGE, BLACK = (249, 60, 29, 255), (10, 10, 12, 255)
CAP_Y, LABEL_Y = 400, 1490  # inside the Shorts safe area
# word in the VO -> label held on screen while its part is glowing
LABELS = {"jib.": "JIB", "counterweight.": "COUNTERWEIGHT", "twenty": "20 TONS", "jacks": "JACK",
          "six": "6 M SECTION", "eighty": "80 M", "lifts.": "LIFT SHAFT", "smaller": "DERRICK"}
T = json.load(open(os.path.join(HERE, "timing.json")))
words = T["words"]
dur = T["duration"] / TEMPO + 0.8


def text_size(d, text, font):
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=font)
    return x0, y0, x1 - x0, y1 - y0


def pill(im, text, font, cy, fill, ink, glow=None, pad=(38, 22)):
    d = ImageDraw.Draw(im)
    x0, y0, tw, th = text_size(d, text, font)
    box = [(W - tw) / 2 - pad[0], cy - th / 2 - pad[1], (W + tw) / 2 + pad[0], cy + th / 2 + pad[1]]
    if glow:  # soft neon halo behind the pill
        halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(halo).rounded_rectangle(box, radius=20, fill=glow)
        im.alpha_composite(halo.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle(box, radius=20, fill=fill)
    d.text(((W - tw) / 2 - x0, cy - th / 2 - y0), text, font=font, fill=ink)


def clean(w):
    return re.sub(r"^[\W]+|[^\w'’]+$", "", w).upper()


def caption_layer(mid):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    now = [w for w in words if w["start"] / TEMPO <= mid < w["end"] / TEMPO + 0.12]
    if now:
        pill(im, clean(now[-1]["w"]), BIG, CAP_Y, BLACK, ORANGE, (255, 39, 13, 170))
    for l0, l1, text in labels:
        if l0 <= mid < l1:
            # up by the counterweight: the low spot would cover the worker's face in this shot
            pill(im, text, SMALL, 565 if text in ("20 TONS", "COUNTERWEIGHT") else LABEL_Y, ORANGE, BLACK)
    return im


labels = []
for w in words:
    k = w["w"].lower()
    if k in LABELS and not any(l[2] == LABELS[k] for l in labels):
        labels.append((w["start"] / TEMPO, w["start"] / TEMPO + 2.2, LABELS[k]))

if "--test" in sys.argv:
    i = sys.argv.index("--test")
    bg = Image.open(sys.argv[i + 1]).convert("RGBA")
    bg.alpha_composite(caption_layer(float(sys.argv[i + 2])))
    p = os.path.join(HERE, "preview", "caption_test.jpg")
    bg.convert("RGB").save(p, quality=92)
    print(p)
    sys.exit()

# one still per time span, from every moment a caption or label changes
cuts = sorted({0.0, dur} | {w["start"] / TEMPO for w in words} | {w["end"] / TEMPO + 0.12 for w in words}
              | {t for l in labels for t in l[:2]})
cuts = [c for c in cuts if c <= dur]
caps = os.path.join(HERE, "caps_v3")
os.makedirs(caps, exist_ok=True)
lines = []
for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
    p = os.path.join(caps, f"c{i:05d}.png")
    caption_layer((a + b) / 2).save(p)
    lines += [f"file '{p.replace(os.sep, '/')}'", f"duration {b - a:.4f}"]
lines.append(lines[-2])
lst = os.path.join(caps, "list.txt")
open(lst, "w").write("\n".join(lines))


def stamp(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


# a standard subtitle file too, grouped by sentence-sized chunks, for uploading
with open(os.path.join(HERE, "crane_short_v3.srt"), "w", encoding="utf-8") as f:
    chunk, n = [], 1
    for i, w in enumerate(words):
        chunk.append(w)
        if len(chunk) >= 7 or w["w"][-1] in ".,:" or i == len(words) - 1:
            f.write(f"{n}\n{stamp(chunk[0]['start'] / TEMPO)} --> {stamp(chunk[-1]['end'] / TEMPO)}\n"
                    + " ".join(c["w"] for c in chunk) + "\n\n")
            chunk, n = [], n + 1

out = os.path.join(HERE, "crane_short_v3.mp4")
subprocess.check_call([
    "ffmpeg", "-v", "error", "-stats", "-y",
    "-framerate", str(FPS), "-start_number", "1", "-i", os.path.join(HERE, "frames_v3", "f%04d.jpg"),
    "-f", "concat", "-safe", "0", "-i", lst,
    "-i", os.path.join(HERE, "vo.mp3"),
    "-filter_complex", f"[0:v]vignette=PI/6,eq=contrast=1.06:saturation=1.08[g];"
                       f"[1:v]fps={FPS},format=rgba[c];[g][c]overlay=eof_action=pass,scale=out_range=tv,format=yuv420p[v];"
                       f"[2:a]atempo={TEMPO},loudnorm=I=-14:TP=-1.5:LRA=11[a]",
    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-color_range", "tv",
    "-c:a", "aac", "-b:a", "192k", "-ar", "44100", out])
print("wrote", out)
