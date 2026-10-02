"""LOOP step 7: slice the transcript by marker into dialogue.json, with ALIGN.

PLAYBOOK 3.5: a marker sits where the on-screen title appears, which lags the
narrator naming the machine. So after the naive slice, snap each item's start
BACK to the earliest subtitle line (inside a search window) that first mentions a
distinctive word of that item's name. Without this, sentences get cut mid-word
and the wrong narration lands under the wrong item.

ASR mangles brand names, so name matching is fuzzy.
"""
import difflib
import json
import re

from resolve_env import fps_of, frames_to_tc

BACK_S, FWD_S = 25.0, 8.0      # how far to hunt around the marker
FUZZ = 0.82

# words too generic to identify an item by
GENERIC = {
    "THE", "AND", "WITH", "FOR", "TRUCK", "TRUCKS", "CRANE", "CRANES", "COMPANY",
    "RIGGING", "TRANSPORT", "TRANSPORTS", "TRANSPORTED", "WORKS", "OIL", "FIELD",
    "BLAST", "FURNACE", "REPLACEMENT", "RIG", "MOVE", "TOWER", "GROUP", "MOVER",
    "AGRO", "BRIDGE", "HEAVY", "LOAD", "LOADS",
}

data = json.load(open("items.json"))
names = json.load(open("names.json"))["items"]
subs = json.load(open("subs.json"))
fps = data["fps"]
back, fwd = int(BACK_S * fps), int(FWD_S * fps)

WORD = re.compile(r"[A-Z0-9][A-Z0-9.\-]*")

def keywords(name):
    out = []
    for w in WORD.findall(name.upper()):
        w = w.strip(".-")
        if len(w) < 3 or w in GENERIC:
            continue
        out.append(w)
    return out

def line_has(text, keys):
    toks = WORD.findall(text.upper())
    for k in keys:
        for t in toks:
            if t == k:
                return k
            if len(k) >= 5 and difflib.SequenceMatcher(None, k, t).ratio() >= FUZZ:
                return k
    return None

items = data["items"]

# --- pass 1: ALIGN each start independently ---
# The guard is the previous item's ALIGNED START, not its end: ends are derived
# from starts in pass 2, so using them here would clamp the window to the marker
# itself and silently disable the whole backward snap.
aligned = []
for it in items:
    marker = it["frame"]
    keys = keywords(names[str(it["n"])]["name"])
    lo = max(data["start"], marker - back)
    if aligned:
        lo = max(lo, aligned[-1][0] + 1)         # never steal the previous item
    hit, hit_key = None, None
    for s in subs:
        if s["start"] < lo:
            continue
        if s["start"] >= marker + fwd:
            break
        k = line_has(s["text"], keys)
        if k:
            hit, hit_key = s["start"], k
            break
    aligned.append((hit if hit is not None else marker, hit_key))

# --- pass 2: ends follow the aligned starts, so items stay contiguous ---
out = []
for idx, it in enumerate(items):
    n, marker = it["n"], it["frame"]
    start, hit_key = aligned[idx]
    nxt = aligned[idx + 1][0] if idx + 1 < len(items) else data["end"]
    meta = names[str(n)]

    lines = [s for s in subs if start <= s["start"] < nxt]
    text = " ".join(s["text"] for s in lines)
    text = re.sub(r"\s*\((?:[^)]*)\)\s*", " ", text)      # drop (air whooshing)
    text = re.sub(r"\s+", " ", text).strip()

    out.append({
        "n": n, "marker": marker, "start": start, "end": nxt,
        "shift_frames": marker - start,
        "shift_s": round((marker - start) / fps, 1),
        "matched_on": hit_key,
        "name": meta["name"], "link": meta["link"],
        "n_lines": len(lines), "n_words": len(text.split()),
        "text": text,
    })

print(f"{'#':>3} {'marker':>9} {'aligned':>9} {'shift':>7} {'match':<12} "
      f"{'lines':>5} {'words':>5}")
for o in out:
    print(f"{o['n']:>3} {frames_to_tc(o['marker'], fps)} {frames_to_tc(o['start'], fps)} "
          f"{o['shift_s']:>6}s {str(o['matched_on'] or '-'):<12} "
          f"{o['n_lines']:>5} {o['n_words']:>5}")

miss = [o["n"] for o in out if o["matched_on"] is None]
print(f"\naligned={len(out)-len(miss)}/{len(out)}  unmatched={miss}")
json.dump(out, open("dialogue.json", "w"), indent=2)
print("wrote dialogue.json")
