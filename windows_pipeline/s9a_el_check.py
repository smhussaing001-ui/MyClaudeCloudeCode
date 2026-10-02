"""ElevenLabs auth + quota + voice list. Read-only, costs no credits.

Key comes from the environment, never from source (PLAYBOOK 3.7). The key itself
is never printed.
"""
import os
import sys

import requests

key = os.environ.get("ELEVENLABS_API_KEY")
if not key:
    sys.exit("ELEVENLABS_API_KEY not set — set it and restart, then re-run.")
H = {"xi-api-key": key}
BASE = "https://api.elevenlabs.io/v1"

# Restricted keys can lack user_read while still being fine for TTS — a 401 with
# status 'missing_permissions' means the key IS valid, just scoped. Don't abort.
r = requests.get(f"{BASE}/user/subscription", headers=H, timeout=60)
print("GET /user/subscription ->", r.status_code)
if r.status_code == 200:
    s = r.json()
    used, lim = s.get("character_count"), s.get("character_limit")
    print(f"  tier      : {s.get('tier')}")
    print(f"  characters: {used}/{lim}  "
          f"remaining={lim - used if None not in (used, lim) else '?'}")
else:
    d = r.json().get("detail", {})
    print(f"  {d.get('status')}: {d.get('message')}")
    print("  -> quota unknown; key is scoped. Continuing.")

r = requests.get(f"{BASE}/voices", headers=H, timeout=60)
print("\nGET /voices ->", r.status_code)
if r.status_code != 200:
    d = r.json().get("detail", {})
    sys.exit(f"  cannot list voices: {d.get('status')}: {d.get('message')}\n"
             "  -> the key needs voices_read, or give me the voice ID directly.")
voices = r.json().get("voices", [])
print(f"  {len(voices)} voices available\n")
print(f"  {'voice_id':<24} {'name':<26} {'category':<12} labels")
for v in voices:
    labels = ", ".join(f"{k}={x}" for k, x in (v.get("labels") or {}).items())
    print(f"  {v['voice_id']:<24} {v['name'][:25]:<26} "
          f"{str(v.get('category'))[:11]:<12} {labels[:60]}")
