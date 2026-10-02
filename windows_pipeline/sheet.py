import os
from PIL import Image, ImageDraw, ImageFont
OUT = "stills"
nums = [8,9]
strips = [(n, Image.open(f"{OUT}/strip_{n:02d}.png")) for n in nums]
w = max(s.width for _, s in strips) + 70
h = sum(s.height + 6 for _, s in strips)
sheet = Image.new("RGB", (w, h), "white")
try:
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 46)
except OSError:
    font = ImageFont.load_default()
d = ImageDraw.Draw(sheet)
y = 0
for n, s in strips:
    sheet.paste(s, (70, y))
    d.text((14, y + s.height // 2 - 28), str(n), fill="black", font=font)
    d.line([(0, y + s.height + 3), (w, y + s.height + 3)], fill="black", width=2)
    y += s.height + 6
sheet.save(f"{OUT}/sheet_8_9.png")
print(sheet.size)
