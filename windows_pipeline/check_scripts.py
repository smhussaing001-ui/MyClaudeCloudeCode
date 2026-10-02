"""Guard: scripts must be shuffle-safe (self-contained) and fit their span.

Segments may be reordered later, so any script that references a neighbouring
item, its position in the running order, or an introduction made elsewhere would
break the moment the order changes.
"""
import json
import re

RATE = 155 / 11.0            # chars/sec, measured from the ElevenLabs test clip

# order-dependent language, checked at the start of a script or as a whole word
BANNED = [
    r"^\s*(instead|also|then|next|finally|moving forward|as mentioned|likewise)\b",
    r"\b(instead|as we saw|as mentioned|earlier in this|previously|the other (crane|truck|one))\b",
    r"\b(first|second|third|fourth|fifth|last) (on (our|the) list|up)\b",
    r"\bnumber (one|two|three|four|five|six|seven|eight|nine|ten)\b",
    r"\b(coming up|up next|stay tuned)\b",
]

scripts = json.load(open("scripts.json"))
items = {str(i["n"]): i for i in json.load(open("items.json"))["items"]}
names = json.load(open("names.json"))["items"]

bad = 0
print(f"{'#':>3} {'words':>5} {'chars':>5} {'est':>7} {'span':>8}  {'fit':<8} shuffle-safe")
for n in sorted((k for k in scripts if k.isdigit()), key=int):
    t = scripts[n]["script"]
    hits = [m.group(0).strip() for p in BANNED
            for m in re.finditer(p, t, re.I)]
    # a script must name its own subject, not rely on a neighbour for it
    key = re.split(r"[^A-Za-z]+", names[n]["name"])[0].lower()
    self_named = key[:5] in t.lower().replace(" ", "") or key in t.lower()
    est, span = len(t) / RATE, items[n]["len_s"]
    ok_fit = est < span
    flag = "OK" if (not hits and self_named) else ", ".join(hits) or "UNNAMED SUBJECT"
    if hits or not self_named or not ok_fit:
        bad += 1
    print(f"{n:>3} {len(t.split()):>5} {len(t):>5} {est:>6.1f}s {span:>7.1f}s  "
          f"{'OK' if ok_fit else 'OVERRUN':<8} {flag}")

tot = sum(len(scripts[n]["script"]) for n in scripts if n.isdigit())
print(f"\ntotal {tot} chars  ~{tot/RATE/60:.1f} min  |  problems: {bad}")
