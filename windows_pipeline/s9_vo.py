"""LOOP step 9: generate voiceover with ElevenLabs.

PLAYBOOK 3.7: key from ENV, never hard-coded. A 200 response with an audio body
is success; a JSON body is an error even when the status looks fine, so the body
is sniffed rather than trusted.

    python s9_vo.py --test "some words"     one throwaway clip -> vo/test.mp3
    python s9_vo.py 1                       item 1 from scripts.json
    python s9_vo.py                         every item in scripts.json
"""
import json
import os
import subprocess
import sys

import requests

CFG = json.load(open("vo_config.json"))
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vo")
URL = "https://api.elevenlabs.io/v1/text-to-speech/" + CFG["voice_id"]

key = os.environ.get("ELEVENLABS_API_KEY")
if not key:
    sys.exit("ELEVENLABS_API_KEY not set.")
H = {"xi-api-key": key, "Content-Type": "application/json"}


def probe(path):
    """Duration via ffprobe, so we can sanity-check length without listening."""
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], capture_output=True, text=True)
        return float(p.stdout.strip())
    except (ValueError, OSError):
        return None


def synth(text, path):
    body = {"text": text, "model_id": CFG["model_id"],
            "voice_settings": CFG["voice_settings"]}
    r = requests.post(URL, headers=H, json=body, timeout=180)
    ctype = r.headers.get("content-type", "")
    if r.status_code != 200 or "application/json" in ctype:
        try:
            d = r.json().get("detail", {})
            msg = f"{d.get('status')}: {d.get('message')}" if isinstance(d, dict) else str(d)
        except ValueError:
            msg = r.text[:200]
        print(f"    FAILED {r.status_code} {msg}")
        return False
    with open(path, "wb") as f:
        f.write(r.content)
    dur = probe(path)
    print(f"    {os.path.basename(path)}  {len(r.content)/1024:.0f} KB  "
          f"{f'{dur:.1f}s' if dur else 'duration ?'}  chars={len(text)}")
    return True


os.makedirs(OUT, exist_ok=True)
print(f"voice: {CFG['voice_name']} ({CFG['voice_id']})  model={CFG['model_id']}")

if "--test" in sys.argv:
    text = sys.argv[sys.argv.index("--test") + 1]
    print(f"\nTEST: {text!r}")
    sys.exit(0 if synth(text, os.path.join(OUT, "test.mp3")) else 1)

scripts = json.load(open("scripts.json"))
wanted = [a for a in sys.argv[1:] if a.isdigit()]
total = 0
for n in sorted((k for k in scripts if k.isdigit()), key=int):   # skip _rules etc
    if wanted and n not in wanted:
        continue
    text = scripts[n]["script"]
    print(f"\n  item {n}: {scripts[n]['name']}")
    if synth(text, os.path.join(OUT, f"clip_{int(n):02d}.mp3")):
        total += len(text)
print(f"\ndone | characters billed this run ~{total}")
