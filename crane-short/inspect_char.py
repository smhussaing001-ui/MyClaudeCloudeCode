"""List what the CC0 character pack contains and render one test pose."""
import math

import bpy

GLB = r"D:\Claude\crane-short\assets\ual\x\Animation Library[Standard]\Godot\AnimationLibrary_Godot_Standard.glb"
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in bpy.data.objects:
    print("OBJ", o.type, o.name, [round(v, 2) for v in o.dimensions], o.parent.name if o.parent else "")
    if o.type == "MESH":
        print("  verts", len(o.data.vertices), "mats", [m.name for m in o.data.materials])
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("BONES", [b.name for b in arm.data.bones])
for a in sorted(bpy.data.actions, key=lambda a: a.name):
    print("ACT", a.name, round(a.frame_range[1] - a.frame_range[0]))
