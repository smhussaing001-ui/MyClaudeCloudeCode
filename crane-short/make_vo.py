"""Generate the voiceover with ElevenLabs and work out word + beat timings.

Key comes from ELEVENLABS_API_KEY. Beats are read from script.md, joined into one
take so the delivery flows, and timed from the character alignment.

    python make_vo.py            -> vo.mp3, timing.json
"""
import base64
import json
import os
import re
import sys

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "..", "windows_pipeline", "vo_config.json")))

key = os.environ.get("ELEVENLABS_API_KEY") or os.environ.get("ELEVEN_API_KEY")
if not key:
    sys.exit("ELEVENLABS_API_KEY not set.")

beats = re.findall(r"^\d+\. \*\*(\w+)\*\* — (.+)$",
                   open(os.path.join(HERE, "script.md"), encoding="utf-8").read(), re.M)
text, spans = "", []
for name, line in beats:
    spans.append((name, len(text), len(text) + len(line)))
    text += line + " "
text = text.strip()

r = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{CFG['voice_id']}/with-timestamps",
    headers={"xi-api-key": key, "Content-Type": "application/json"},
    json={"text": text, "model_id": CFG["model_id"], "voice_settings": CFG["voice_settings"]},
    timeout=300)
if r.status_code != 200:
    sys.exit(f"FAILED {r.status_code}: {r.text[:300]}")
d = r.json()
with open(os.path.join(HERE, "vo.mp3"), "wb") as f:
    f.write(base64.b64decode(d["audio_base64"]))

al = d["alignment"]
chars, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
assert "".join(chars) == text, "alignment does not match text"

words = [{"w": m.group(), "start": st[m.start()], "end": en[m.end() - 1]}
         for m in re.finditer(r"\S+", text)]
out = {
    "duration": en[-1],
    "beats": [{"name": n, "start": st[a], "end": en[b - 1]} for n, a, b in spans],
    "words": words,
}
json.dump(out, open(os.path.join(HERE, "timing.json"), "w"), indent=1)
print(f"{len(text)} chars, {en[-1]:.1f}s")
for b in out["beats"]:
    print(f"  {b['name']:14s} {b['start']:6.2f} {b['end']:6.2f}")
