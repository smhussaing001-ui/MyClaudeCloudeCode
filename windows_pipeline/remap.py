"""Insert a new item and shift every later item's number by one.

Item numbers are ordinals derived from marker order, so inserting a marker
renumbers everything after it. names.json / scripts.json / vo/clip_NN.mp3 are all
keyed by that ordinal, so they must shift together or they silently desync.

Usage: python remap.py <insert_after_item_n>        (dry run)
       python remap.py <insert_after_item_n> --apply
"""
import json
import os
import shutil
import sys

after = int(sys.argv[1])
apply = "--apply" in sys.argv
BK = "backup_pre_insert"

names = json.load(open("names.json"))
scripts = json.load(open("scripts.json"))
old_ns = sorted((k for k in names["items"] if k.isdigit()), key=int)
moves = [(int(n), int(n) + 1) for n in old_ns if int(n) > after]
moves.sort(reverse=True)                       # descending: never clobber

print(f"insert after item {after} -> {len(moves)} items shift +1")
for o, n in reversed(moves):
    print(f"  {o:>2} -> {n:>2}  {names['items'][str(o)]['name']}")

if not apply:
    print("\ndry run — pass --apply to write")
    sys.exit(0)

os.makedirs(BK, exist_ok=True)
for f in ("names.json", "scripts.json", "items.json"):
    shutil.copy2(f, os.path.join(BK, f))
if os.path.isdir("vo") and not os.path.isdir(os.path.join(BK, "vo")):
    shutil.copytree("vo", os.path.join(BK, "vo"))
print(f"\nbacked up to {BK}/")

new_names = {k: v for k, v in names["items"].items() if not k.isdigit() or int(k) <= after}
new_scripts = {k: v for k, v in scripts.items() if not k.isdigit() or int(k) <= after}
for o, n in moves:
    new_names[str(n)] = names["items"][str(o)]
    new_scripts[str(n)] = scripts[str(o)]
names["items"] = new_names
json.dump(names, open("names.json", "w"), indent=2)
json.dump(new_scripts, open("scripts.json", "w"), indent=2)
print(f"rewrote names.json ({len(new_names)} keys) and scripts.json")

renamed = 0
for o, n in moves:                             # descending order avoids collisions
    src, dst = f"vo/clip_{o:02d}.mp3", f"vo/clip_{n:02d}.mp3"
    if os.path.exists(src):
        os.replace(src, dst)
        renamed += 1
print(f"renamed {renamed} vo clips")
print(f"vo now: {sorted(os.listdir('vo'))}")
