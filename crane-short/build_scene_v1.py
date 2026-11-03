"""Build the whole tower-crane Short in Blender, timed from timing.json.

    blender -b -P build_scene.py -- preview 100 500 900    low-res test stills
    blender -b -P build_scene.py                           save crane.blend only
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = r"D:\Claude\crane-short"
FPS = 30
TEMPO = 1.1  # the VO is sped up by this factor in finish.py
T = json.load(open(os.path.join(HERE, "timing.json")))
random.seed(7)

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)


def F(t):
    return int(round(t / TEMPO * FPS)) + 1


BEATS = {b["name"]: b for b in T["beats"]}
ORDER = [b["name"] for b in T["beats"]]
LAST = F(T["duration"]) + 24


def B(name):
    """First and last frame of a beat; a beat runs until the next one starts."""
    i = ORDER.index(name)
    return F(BEATS[name]["start"]), (F(BEATS[ORDER[i + 1]]["start"]) - 1 if i + 1 < len(ORDER) else LAST)


def W(beat, word):
    """Frame at which `word` is first spoken inside `beat`."""
    a, b = BEATS[beat]["start"], BEATS[beat]["end"]
    for w in T["words"]:
        if a <= w["start"] <= b and w["w"].lower().startswith(word):
            return F(w["start"])
    raise KeyError(word)


# ---------------------------------------------------------------- materials
hz_group = bpy.data.node_groups.new("Haze", "ShaderNodeTree")
hz_group.interface.new_socket("Fac", in_out="OUTPUT", socket_type="NodeSocketFloat")
n = hz_group.nodes
out = n.new("NodeGroupOutput")
cam_n = n.new("ShaderNodeCameraData")
mr = n.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = 120
mr.inputs["From Max"].default_value = 1500
mr.inputs["To Max"].default_value = 0.85
hz_group.links.new(cam_n.outputs["View Distance"], mr.inputs["Value"])
hz_group.links.new(mr.outputs[0], out.inputs[0])

hz_color = (0.70, 0.80, 0.90, 1)
HAZE_RGBS = []


def finish_mat(m, base_socket, rough=0.8, emission=None):
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    bs.inputs["Roughness"].default_value = rough
    if base_socket is not None:
        nt.links.new(base_socket, bs.inputs["Base Color"])
    g = nt.nodes.new("ShaderNodeGroup")
    g.node_tree = hz_group
    rgb = nt.nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value = hz_color
    HAZE_RGBS.append(rgb)
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(rgb.outputs[0], em.inputs[0])
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(g.outputs[0], mix.inputs[0])
    nt.links.new(bs.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs[0])


MATS = {}


def flat(col, rough=0.7):
    k = (tuple(col), rough)
    if k in MATS:
        return MATS[k]
    m = bpy.data.materials.new(f"flat{len(MATS)}")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1)
    finish_mat(m, None, rough)
    MATS[k] = m
    return m


def glow(col, power=3):
    m = bpy.data.materials.new("glow")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = (*col, 1)
    e.inputs[1].default_value = power
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


# a one-window facade tile, multiplied by each building's own tint
SZ = 64
img = bpy.data.images.new("facade", SZ, SZ)
px = []
for y in range(SZ):
    for x in range(SZ):
        win = 18 <= x < 46 and 16 <= y < 50
        sill = 18 <= x < 46 and 12 <= y < 16
        c = (0.12, 0.17, 0.25) if win else (0.72, 0.72, 0.72) if sill else (1, 1, 1)
        px += [*c, 1]
img.pixels = px
img.pack()

wall_mat = bpy.data.materials.new("wall")
wall_mat.use_nodes = True
nt = wall_mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
attr = nt.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "tint"
mult = nt.nodes.new("ShaderNodeMixRGB")
mult.blend_type = "MULTIPLY"
mult.inputs[0].default_value = 1
nt.links.new(tex.outputs[0], mult.inputs[1])
nt.links.new(attr.outputs[0], mult.inputs[2])
finish_mat(wall_mat, mult.outputs[0], 0.6)

roof_mat = bpy.data.materials.new("roof")
roof_mat.use_nodes = True
attr = roof_mat.node_tree.nodes.new("ShaderNodeAttribute")
attr.attribute_name = "tint"
finish_mat(roof_mat, attr.outputs[0], 0.9)


# ---------------------------------------------------------------- meshes
class MB:
    """Accumulates geometry so thousands of parts become one fast mesh."""

    def __init__(self):
        self.v, self.f, self.uv, self.col, self.mi = [], [], [], [], []

    def add(self, verts, faces, col=(1, 1, 1), mat=0, uvs=None):
        s = len(self.v)
        self.v += [tuple(p) for p in verts]
        for i, fc in enumerate(faces):
            self.f.append([s + j for j in fc])
            self.uv.append(uvs[i] if uvs else [(0, 0)] * len(fc))
            self.col.append(col)
            self.mi.append(mat)

    def box(self, c, s, col=(1, 1, 1), tile=None):
        """Axis-aligned box. tile=metres per window gives facade UVs; the top uses slot 1."""
        x, y, z = c
        a, b, h = s[0] / 2, s[1] / 2, s[2] / 2
        vs = [(x - a, y - b, z - h), (x + a, y - b, z - h), (x + a, y + b, z - h), (x - a, y + b, z - h),
              (x - a, y - b, z + h), (x + a, y - b, z + h), (x + a, y + b, z + h), (x - a, y + b, z + h)]
        sides = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        cap = [(3, 2, 1, 0), (4, 5, 6, 7)]
        if tile:
            for i, fc in enumerate(sides):
                u = round((s[0] if i % 2 == 0 else s[1]) / tile) or 1
                v = round(s[2] / tile) or 1
                self.add(vs, [fc], col, 0, [[(0, 0), (u, 0), (u, v), (0, v)]])
            self.add(vs, cap, col, 1)
        else:
            self.add(vs, sides + cap, col)

    def beam(self, p, q, t=0.12):
        p, q = Vector(p), Vector(q)
        d = (q - p).normalized()
        u = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized() * t / 2
        w = d.cross(u).normalized() * t / 2
        vs = [p - u - w, p + u - w, p + u + w, p - u + w, q - u - w, q + u - w, q + u + w, q - u + w]
        self.add(vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0), (4, 5, 6, 7)])

    def mesh(self, name):
        m = bpy.data.meshes.new(name)
        m.from_pydata(self.v, [], self.f)
        m.update()
        # adding an attribute reallocates storage, so fetch both layers only once both exist
        m.uv_layers.new(name="UV")
        m.color_attributes.new("tint", "FLOAT_COLOR", "CORNER")
        uvs, cols = [], []
        for pi, fc in enumerate(self.f):
            for k in range(len(fc)):
                uvs += self.uv[pi][k]
                cols += (*self.col[pi], 1)
        m.uv_layers["UV"].data.foreach_set("uv", uvs)
        m.color_attributes["tint"].data.foreach_set("color", cols)
        m.polygons.foreach_set("material_index", self.mi)
        m.update()
        return m


scene = bpy.context.scene
col = scene.collection


def obj(name, data, mats=(), parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, data)
    col.objects.link(o)
    for m in mats:
        if len(o.data.materials) < len(mats):
            o.data.materials.append(m)
    o.parent = parent
    o.location = loc
    return o


def part(name, mb, mat, parent=None, loc=(0, 0, 0)):
    return obj(name, mb.mesh(name), [mat], parent, loc)


def empty(name, parent=None, loc=(0, 0, 0)):
    return obj(name, None, (), parent, loc)


def boxpart(name, c, s, col_, parent=None, loc=(0, 0, 0)):
    mb = MB()
    mb.box(c, s)
    return part(name, mb, flat(col_), parent, loc)


# ---------------------------------------------------------------- animation helpers
def key(o, path, f, val):
    setattr(o, path, val)
    o.keyframe_insert(path, frame=f)


def pop(o, f, dur=8, size=(1, 1, 1)):
    key(o, "scale", f, (0, 0, 0))
    key(o, "scale", f + dur, size)


VIS = []


def vis(o, *ranges):
    VIS.append((o, ranges))


def apply_vis():
    def walk(o):
        yield o
        for c in o.children:
            yield from walk(c)

    for root, ranges in VIS:
        for o in walk(root):
            o.hide_render = True
            o.keyframe_insert("hide_render", frame=1)
            for a, b in ranges:
                o.hide_render = False
                o.keyframe_insert("hide_render", frame=a)
                o.hide_render = True
                o.keyframe_insert("hide_render", frame=b + 1)


YELLOW = (0.95, 0.68, 0.05)
RED = (0.75, 0.08, 0.10)
WHITE = (0.92, 0.92, 0.92)
DARK = (0.04, 0.05, 0.07)
STEEL = (0.25, 0.27, 0.3)
CONCRETE = (0.62, 0.62, 0.60)
SEC_DATA = {}


def section_mesh(col_):
    if col_ in SEC_DATA:
        return SEC_DATA[col_]
    mb = MB()
    w, h = 1.0, 6.0
    cs = [(-w, -w), (w, -w), (w, w), (-w, w)]
    for x, y in cs:
        mb.beam((x, y, 0), (x, y, h), 0.2)
    for z0 in (0, 3):
        for i in range(4):
            a, b = cs[i], cs[(i + 1) % 4]
            mb.beam((*a, z0), (*b, z0), 0.1)
            mb.beam((*a, z0), (*b, z0 + 3), 0.1)
    me = mb.mesh("section")
    me.materials.append(flat(col_))
    SEC_DATA[col_] = me
    return me


def make_crane(name, n, col_=YELLOW, chain=False, jib=36.0, cj=12.0, s=1.0, loc=(0, 0, 0)):
    """A rigged tower crane. Returns a dict of the parts the animation needs."""
    root = empty(name, loc=loc)
    root.scale = (s, s, s)
    secs, prev = [], root
    for i in range(n):
        o = obj(f"{name}_sec{i}", section_mesh(col_), (), prev if chain else root,
                (0, 0, 6 if chain and i else 0 if chain else 6 * i))
        secs.append(o)
        if chain:
            prev = o
    top = empty(f"{name}_top", prev if chain else root, (0, 0, 6) if chain else (0, 0, 6 * n))

    mb = MB()
    mb.box((0, 0, 0.5), (3.2, 3.2, 1.0))
    for x, y in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        mb.beam((x, y, 1), (0, 0, 9), 0.18)
    mb.beam((0, 0, 3), (0, 0, 9), 0.12)
    head = part(f"{name}_head", mb, flat(col_), top)

    cab = boxpart(f"{name}_cab", (1.3, -2.3, 1.2), (2.2, 2.2, 2.4), WHITE, head)
    boxpart(f"{name}_win", (1.3, -3.42, 1.4), (1.8, 0.05, 1.5), DARK, cab)
    boxpart(f"{name}_win2", (2.42, -2.3, 1.4), (0.05, 1.8, 1.5), DARK, cab)

    mb = MB()
    bays = int(jib / 3)
    L = jib / bays
    for i in range(bays):
        x0, x1 = 1 + i * L, 1 + (i + 1) * L
        for y in (-0.8, 0.8):
            mb.beam((x0, y, 1), (x1, y, 1), 0.14)
            mb.beam((x0, y, 1), (x0 + L / 2, 0, 2.5), 0.08)
            mb.beam((x0 + L / 2, 0, 2.5), (x1, y, 1), 0.08)
        mb.beam((x0 + L / 2, 0, 2.5), (x1 + L / 2 if i < bays - 1 else x1, 0, 2.5), 0.14)
        mb.beam((x0, -0.8, 1), (x0, 0.8, 1), 0.08)
    mb.beam((0, 0, 9), (jib * 0.65, 0, 2.6), 0.07)
    mb.beam((0, 0, 9), (jib * 0.35, 0, 2.6), 0.07)
    jib_o = part(f"{name}_jib", mb, flat(col_), top)

    mb = MB()
    mb.box((-cj / 2 - 1, 0, 1.0), (cj, 2.4, 0.3))
    mb.beam((0, 0, 9), (-cj, 0, 1.2), 0.07)
    cj_o = part(f"{name}_cj", mb, flat(col_), top)
    weights = [boxpart(f"{name}_w{i}", (0, 0, 0), (2.4, 2.4, 1.2), CONCRETE, cj_o, (-cj + 1.5, 0, 1.75 + 1.25 * i))
               for i in range(4)]

    trolley = boxpart(f"{name}_trolley", (0, 0, 0), (1.6, 1.6, 0.4), DARK, jib_o, (10, 0, 0.8))
    mb = MB()
    mb.beam((0, 0, 0), (0, 0, -1), 0.07)
    cable = part(f"{name}_cable", mb, flat(DARK), trolley)
    hook = boxpart(f"{name}_hook", (0, 0, 0), (0.7, 0.7, 1.0), YELLOW, trolley, (0, 0, -8))
    cable.scale.z = 8
    return dict(root=root, secs=secs, top=top, head=head, cab=cab, jib=jib_o, cj=cj_o, weights=weights,
                trolley=trolley, cable=cable, hook=hook)


def set_hook(c, f, x=None, length=None):
    if x is not None:
        key(c["trolley"], "location", f, (x, 0, 0.8))
    if length is not None:
        key(c["cable"], "scale", f, (1, 1, length))
        key(c["hook"], "location", f, (0, 0, -length))


def make_floors(name, count, w=18.0, hole=6.0, fh=3.5, parent=None):
    """Open concrete frame: one object per storey, slab with a lift-shaft hole."""
    root = empty(name, parent)
    floors = []
    for i in range(count):
        mb = MB()
        a = (w + hole) / 4
        t = (w - hole) / 2
        for sx in (-1, 1):
            mb.box((sx * a, 0, 0), (t, w, 0.35))
            mb.box((0, sx * a, 0), (hole, t, 0.35))
        for x in (-w / 2 + 0.5, -w / 6, w / 6, w / 2 - 0.5):
            for y in (-w / 2 + 0.5, w / 2 - 0.5):
                mb.box((x, y, -fh / 2), (0.5, 0.5, fh))
                mb.box((y, x, -fh / 2), (0.5, 0.5, fh))
        floors.append(part(f"{name}_{i}", mb, flat(CONCRETE), root, (0, 0, (i + 1) * fh)))
    return root, floors


# ---------------------------------------------------------------- city
PASTELS = [(0.85, 0.72, 0.68), (0.72, 0.78, 0.85), (0.86, 0.82, 0.70), (0.80, 0.75, 0.84), (0.75, 0.84, 0.78), (0.90, 0.88, 0.85)]
ROOFS = [(0.45, 0.45, 0.5), (0.55, 0.32, 0.30), (0.5, 0.5, 0.52)]
mb = MB()
step = 44
for ix in range(-34, 35):
    for iy in range(-14, 45):
        x, y = ix * step + random.uniform(-4, 4), iy * step + random.uniform(-4, 4)
        r = math.hypot(x, y)
        if abs(x) < 62 and -135 < y < 50:
            continue  # the site and the camera's corridor
        if r > 1500 or random.random() < 0.06:
            continue
        band = min(r / 900, 1)
        h = random.uniform(14, 34) + band * random.uniform(0, 120) * (1 if random.random() < 0.5 else 0.3)
        if y < -60:
            h = random.uniform(10, 26)
        w = random.uniform(24, 34)
        d = random.uniform(24, 34)
        hue = random.choice(PASTELS)
        mb.box((x, y, h / 2), (w, d, h), hue, tile=3.6)
        mb.box((x, y, h + 0.25), (w, d, 0.5), random.choice(ROOFS), tile=1000)

# the street of houses in the foreground
for i in range(-5, 6):
    x, y = i * 15.5 + 4, -72
    w, d, h = 13.5, 12, random.uniform(9, 13)
    hue = random.choice(PASTELS)
    mb.box((x, y, h / 2), (w, d, h), hue, tile=3.2)
    rc = (0.85, 0.42, 0.25) if i % 2 else (0.5, 0.5, 0.53)
    vs = [(x - w / 2, y - d / 2, h), (x + w / 2, y - d / 2, h), (x + w / 2, y + d / 2, h), (x - w / 2, y + d / 2, h),
          (x - w / 2, y, h + 4.5), (x + w / 2, y, h + 4.5)]
    mb.add(vs, [(0, 1, 5, 4), (2, 3, 4, 5)], rc, 1)
    mb.add(vs, [(1, 2, 5), (3, 0, 4)], hue, 1)
city = obj("city", mb.mesh("city"), [wall_mat, roof_mat])

mb = MB()
mb.box((0, 0, -0.5), (6000, 6000, 1))
part("ground", mb, flat((0.42, 0.43, 0.47)))
mb = MB()
mb.box((0, -52, 0.04), (420, 18, 0.08))
part("road", mb, flat((0.25, 0.26, 0.29)))
mb = MB()
mb.box((0, 0, 0.06), (84, 70, 0.12))
part("site", mb, flat((0.36, 0.24, 0.15)))


def tree(mb_t, mb_f, x, y, s):
    mb_t.box((x, y, 2 * s), (0.5 * s, 0.5 * s, 4 * s))
    for dx, dy, dz, r in [(0, 0, 5, 2.4), (1.5, 0.5, 4.2, 1.6), (-1.4, -0.6, 4.4, 1.7), (0.2, 1.2, 6, 1.5)]:
        ball(mb_f, (x + dx * s, y + dy * s, dz * s), r * s)


def ball(mb_f, c, r):
    rows, cols = 6, 9
    vs = [(c[0], c[1], c[2] + r)]
    for a in range(1, rows):
        th = math.pi * a / rows
        for b in range(cols):
            ph = 2 * math.pi * b / cols
            vs.append((c[0] + r * math.sin(th) * math.cos(ph), c[1] + r * math.sin(th) * math.sin(ph), c[2] + r * math.cos(th)))
    vs.append((c[0], c[1], c[2] - r))
    fs = []
    for b in range(cols):
        fs.append((0, 1 + b, 1 + (b + 1) % cols))
        fs.append((len(vs) - 1, 1 + (rows - 2) * cols + (b + 1) % cols, 1 + (rows - 2) * cols + b))
    for a in range(rows - 2):
        for b in range(cols):
            p = 1 + a * cols
            fs.append((p + b, p + cols + b, p + cols + (b + 1) % cols, p + (b + 1) % cols))
    mb_f.add(vs, fs)


trunks, leaves = MB(), MB()
for i in range(-5, 6):
    tree(trunks, leaves, i * 15.5 + 12, -61, 1.5)
TRUNK, LEAF = (0.22, 0.13, 0.07), (0.16, 0.5, 0.14)
part("trees_t", trunks, flat(TRUNK))
tr_leaf = part("trees_f", leaves, flat(LEAF))
tr_leaf.data.polygons.foreach_set("use_smooth", [True] * len(tr_leaf.data.polygons))
tr_leaf.data.update()

# ---------------------------------------------------------------- light, world, camera
sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 2.1
sun_d.angle = math.radians(2)
sun = obj("sun", sun_d)
sun.rotation_euler = (math.radians(52), 0, math.radians(-35))

world = bpy.data.worlds.new("w")
scene.world = world
world.use_nodes = True
nt = world.node_tree
bg = nt.nodes["Background"]
# the sky keeps full brightness on camera but lights the city more softly
lp = nt.nodes.new("ShaderNodeLightPath")
bs_mix = nt.nodes.new("ShaderNodeMath")
bs_mix.operation = "MULTIPLY_ADD"
bs_mix.inputs[1].default_value = 0.55
bs_mix.inputs[2].default_value = 0.45
nt.links.new(lp.outputs["Is Camera Ray"], bs_mix.inputs[0])
nt.links.new(bs_mix.outputs[0], bg.inputs[1])
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Generated"], sep.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[1].position = 0.45
ramp.color_ramp.elements[0].color = (0.75, 0.85, 0.93, 1)
ramp.color_ramp.elements[1].color = (0.24, 0.48, 0.80, 1)
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1.2, 1.2, 7)
nt.links.new(tc.outputs["Generated"], mp.inputs[0])
noi = nt.nodes.new("ShaderNodeTexNoise")
noi.inputs["Scale"].default_value = 3
noi.inputs["Detail"].default_value = 6
nt.links.new(mp.outputs[0], noi.inputs[0])
cl = nt.nodes.new("ShaderNodeValToRGB")
cl.color_ramp.elements[0].position = 0.52
cl.color_ramp.elements[1].position = 0.68
nt.links.new(noi.outputs[0], cl.inputs[0])
mixc = nt.nodes.new("ShaderNodeMixRGB")
mixc.inputs[2].default_value = (1, 0.98, 0.95, 1)
tint = nt.nodes.new("ShaderNodeRGB")
tint.outputs[0].default_value = (1, 1, 1, 1)
nt.links.new(cl.outputs[0], mixc.inputs[0])
nt.links.new(ramp.outputs[0], mixc.inputs[1])
mult = nt.nodes.new("ShaderNodeMixRGB")
mult.blend_type = "MULTIPLY"
mult.inputs[0].default_value = 1
nt.links.new(mixc.outputs[0], mult.inputs[1])
nt.links.new(tint.outputs[0], mult.inputs[2])
nt.links.new(mult.outputs[0], bg.inputs[0])

cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 30
cam_d.clip_end = 6000
cam = obj("cam", cam_d)
scene.camera = cam
tgt = empty("target")
tc_ = cam.constraints.new("TRACK_TO")
tc_.target = tgt
tc_.track_axis = "TRACK_NEGATIVE_Z"
tc_.up_axis = "UP_Y"


def shot(a, b, *keys):
    """Camera keys as (fraction, position, target) between frames a and b."""
    for frac, pos, aim in keys:
        f = a + int((b - a) * frac)
        key(cam, "location", f, pos)
        key(tgt, "location", f, aim)


# ================================================================ 1. BRANCH
a, b = B("branch")
snap = W("branch", "breaks") + 4
TX = -13
tree_root = empty("tree1")
mb = MB()
mb.beam((TX, 0, 0), (TX, 0, 15), 2.0)
part("trunk", mb, flat(TRUNK), tree_root)
mb = MB()
for dx, dy, dz, r in [(0, 0, 20, 8), (-6, 3, 16, 6), (-3, -5, 15, 5.5), (4, 4, 17, 6)]:
    ball(mb, (TX + dx, dy, dz), r)
crown = part("crown", mb, flat(LEAF), tree_root)
crown.data.polygons.foreach_set("use_smooth", [True] * len(crown.data.polygons))
# the branch pivots where it meets the trunk so it can snap
branch = empty("branch", tree_root, (TX, 0, 13))
mb = MB()
mb.beam((0, 0, 0), (19, 0, 3), 0.8)
part("limb", mb, flat(TRUNK), branch)
mb = MB()
ball(mb, (15, 1, 5), 3)
ball(mb, (19, -1, 4.5), 2.2)
tuft = part("tuft", mb, flat(LEAF), branch)
tuft.data.polygons.foreach_set("use_smooth", [True] * len(tuft.data.polygons))
key(branch, "rotation_euler", a, (0, 0, 0))
key(branch, "rotation_euler", snap - 8, (0, 0.03, 0))
key(branch, "rotation_euler", snap, (0, 0.05, 0))
key(branch, "rotation_euler", snap + 8, (0, 0.85, 0))

ROPE_X = TX + 17
ROPE_TOP = 13 + 2.7
stone = boxpart("stone", (0, 0, 0), (4, 3.4, 2.4), (0.6, 0.6, 0.58), tree_root, (ROPE_X, 0, 1.2))
key(stone, "location", a + 45, (ROPE_X, 0, 1.2))
key(stone, "location", snap - 2, (ROPE_X, 0, 7))
key(stone, "location", snap + 10, (ROPE_X, 0, 1.2))
mb = MB()
mb.beam((0, 0, 0), (0, 0, -1), 0.14)
rope = part("rope", mb, flat((0.8, 0.7, 0.45)), tree_root, (ROPE_X, 0, ROPE_TOP))
key(rope, "scale", a + 45, (1, 1, ROPE_TOP - 2.3))
key(rope, "scale", snap - 2, (1, 1, ROPE_TOP - 8.1))
mb = MB()
mb.beam((ROPE_X + 11, -3, 2.6), (ROPE_X, 0, ROPE_TOP), 0.14)
rope2 = part("rope2", mb, flat((0.8, 0.7, 0.45)), tree_root)
person = empty("person", tree_root, (ROPE_X + 11.3, -3, 0))
boxpart("body", (0, 0, 1.6), (0.6, 0.4, 1.2), (0.85, 0.2, 0.1), person)
boxpart("legs", (0, 0, 0.5), (0.5, 0.35, 1.0), (0.1, 0.15, 0.3), person)
boxpart("head_p", (0, 0, 2.5), (0.42, 0.42, 0.42), (0.9, 0.7, 0.55), person)
vis(tree_root, (a, b))
vis(rope, (a, snap + 1))
vis(rope2, (a, snap + 1))
shot(a, b, (0, (-2, -50, 6), (1, 0, 15)), (0.6, (2, -47, 6), (2, 0, 14)), (1, (4, -45, 5), (3, 0, 12)))

# ================================================================ 2-4. JIB, TIP, COUNTERWEIGHT
a2, b2 = B("jib")
a3, b3 = B("tip")
a4, b4 = B("counterweight")
A = make_crane("A", 5)
for i, s in enumerate(A["secs"]):
    pop(s, a2 + 2 + i * 8, 7)
pop(A["top"], a2 + 44, 6)
jib_f = W("jib", "bolt")
key(A["jib"], "scale", jib_f - 2, (0.001, 1, 1))
key(A["jib"], "scale", jib_f + 30, (1, 1, 1))
pop(A["trolley"], jib_f + 30, 6)
key(A["cj"], "scale", a2, (0, 1, 1))
key(A["cj"], "scale", a4 + 2, (0, 1, 1))
key(A["cj"], "scale", a4 + 28, (1, 1, 1))
A["cab"].hide_render = False
set_hook(A, a3, 8, 18)
set_hook(A, a3 + 6, 8, 18)
set_hook(A, W("tip", "topple") + 4, 33, 18)
load = boxpart("Aload", (0, 0, -1.5), (3, 2.6, 2.2), (0.6, 0.6, 0.58), A["hook"])
pop(load, a3, 6)
key(A["root"], "rotation_euler", a3 + 40, (0, 0, 0))
key(A["root"], "rotation_euler", W("tip", "topple") + 8, (0, 0.30, 0))
key(A["root"], "rotation_euler", b3, (0, 0.33, 0))
w_f = W("counterweight", "pile")
for i, wt in enumerate(A["weights"]):
    z = wt.location.z
    key(wt, "location", w_f + i * 7 - 1, (-10.5, 0, z + 12))
    key(wt, "location", w_f + i * 7 + 7, (-10.5, 0, z))
    pop(wt, w_f + i * 7 - 2, 2)
key(A["root"], "rotation_euler", w_f + 4, (0, 0.33, 0))
key(A["root"], "rotation_euler", w_f + 30, (0, 0, 0))
vis(A["root"], (a2, b4))
shot(a2, b2, (0, (-24, -50, 26), (2, 0, 18)), (1, (-16, -66, 44), (12, 0, 30)))
shot(a3, b3, (0, (-12, -68, 44), (14, 0, 30)), (1, (-2, -74, 40), (18, 0, 24)))
shot(a4, b4, (0, (-38, -40, 46), (-6, 0, 34)), (1, (-28, -66, 48), (6, 0, 30)))

# ================================================================ 5. CLIMB
a, b = B("climb")
C = make_crane("C", 6)
C["cj"].scale = (1, 1, 1)
set_hook(C, a, 14, 14)
bld, floors = make_floors("bldC", 10, w=18, hole=0.2)
bld.location = (19, 2, 0)
grow_end = W("climb", "so") - 2
for i, fl in enumerate(floors):
    if i < 5:
        continue
    pop(fl, a + 3 + (i - 5) * max((grow_end - a - 10) // 7, 3), 5)
jack = W("climb", "jacks")
top0, top1 = 36, 42
key(C["top"], "location", jack, (0, 0, top0))
key(C["top"], "location", jack + 45, (0, 0, top1))
# red climbing frame, carried by the top, so the gap opens inside it
mb = MB()
for x, y in [(-1.6, -1.6), (1.6, -1.6), (1.6, 1.6), (-1.6, 1.6)]:
    mb.beam((x, y, 0), (x, y, -7), 0.3)
mb.box((0, 0, -7), (4, 4, 0.3))
part("Ccage", mb, flat(RED), C["top"])
new_sec = obj("Cnew", section_mesh(YELLOW), (), C["root"], (14, 0, top0))
key(new_sec, "location", jack + 45, (14, 0, top0))
key(new_sec, "location", W("climb", "slides") + 18, (0, 0, top0))
vis(C["root"], (a, b))
vis(bld, (a, b))
shot(a, jack - 1, (0, (-30, -78, 22), (6, 0, 20)), (1, (-34, -78, 40), (6, 0, 30)))
shot(jack, b, (0, (-16, -26, 46), (2, 0, 40)), (1, (-20, -24, 42), (4, 0, 40)))

# ================================================================ 6. WIND
a, b = B("wind")
D = make_crane("D", 14, chain=True)
mb = MB()
mb.box((20, 4, 37), (20, 20, 74), (0.72, 0.72, 0.75), tile=3.6)
block = obj("block6", mb.mesh("block6"), [wall_mat, roof_mat])
gust = W("wind", "flexes")
f = gust - 10
amp = 0.018
phase = 1
keys = [(a, 0.0), (gust - 10, 0.0)]
while f < b:
    f += 16
    keys.append((f, amp * phase))
    phase = -phase * 0.92
    amp = 0.030
for s in D["secs"][1:]:
    for fr, ang in keys:
        key(s, "rotation_euler", fr, (0, ang, 0))
for i in range(9):
    mb = MB()
    mb.box((0, 0, 0), (22, 0.08, 0.14))
    st = part(f"streak{i}", mb, glow((1, 1, 1), 2))
    z = 30 + i * 7.5
    y = random.uniform(-14, -6)
    for k in range(3):
        f0 = gust + i * 3 + k * 26 - 10
        key(st, "location", f0, (-70, y, z))
        key(st, "location", f0 + 25, (80, y, z))
    vis(st, (gust - 10, b))
vis(D["root"], (a, b))
vis(block, (a, b))
shot(a, b, (0, (-20, -128, 62), (6, 0, 56)), (1, (-34, -122, 72), (8, 0, 64)))

# ================================================================ 7. SHAFT
a, b = B("shaft")
fh = 3.5
E = make_crane("E", 6)
bld2, fl2 = make_floors("bldE", 18, w=20, hole=5.0, fh=fh)
for i, fl in enumerate(fl2):
    if i < 8:
        continue
j1, j2 = W("shaft", "jacks"), W("shaft", "braces") + 12
key(E["root"], "location", a, (0, 0, 7))
key(E["root"], "location", W("shaft", "indoors"), (0, 0, 7))
key(E["root"], "location", j1 + 20, (0, 0, 7 + 2 * fh))
key(E["root"], "location", j2 + 20, (0, 0, 7 + 4 * fh))
for i, fl in enumerate(fl2[8:12]):
    pop(fl, a + 10 + i * 18, 6)
for i, fl in enumerate(fl2[12:15]):
    pop(fl, j1 + 26 + i * 16, 6)
for i, fl in enumerate(fl2[15:]):
    fl.scale = (0, 0, 0)
    key(fl, "scale", a, (0, 0, 0))
# collars that grip the slabs
mb = MB()
for z in (1, 13):
    for sx in (-1, 1):
        mb.box((sx * 2.0, 0, z), (1.2, 5.2, 0.4))
        mb.box((0, sx * 2.0, z), (5.2, 1.2, 0.4))
part("Ecollar", mb, flat(RED), E["root"])
set_hook(E, a, 15, 10)
vis(E["root"], (a, b))
vis(bld2, (a, b))
shot(a, b, (0, (30, -46, 36), (0, 0, 32)), (0.5, (36, -46, 48), (0, 0, 42)), (1, (34, -50, 62), (0, 0, 54)))

# ================================================================ 8-10. ROOF
a8, b8 = B("stuck")
a9, b9 = B("derrick")
a10, b10 = B("smaller")
a11, b11 = B("end")
H = 150.0
mb = MB()
mb.box((0, 0, H / 2), (24, 24, H), (0.18, 0.28, 0.46), tile=3.4)
mb.box((0, 0, H + 0.6), (22, 22, 1.2), (0.6, 0.6, 0.6), tile=1000)
tower = obj("skyscraper", mb.mesh("skyscraper"), [wall_mat, roof_mat])
G = make_crane("G", 5, s=1, jib=30, loc=(0, 0, H))
set_hook(G, a8, 12, 10)
vis(tower, (a8, LAST))
vis(G["root"], (a8, b9))
ground = make_crane("Gr", 5, col_=RED, jib=24, cj=8, loc=(46, -28, 0))
vis(ground["root"], (a8, b8))
shot(a8, b8, (0, (22, -44, H + 34), (4, 0, H + 26)), (0.35, (26, -60, H + 26), (4, 0, H + 18)),
     (1, (46, -330, 92), (6, 0, 78)))

# the derrick arrives piece by piece on the big crane's hook
ROOF = H + 1.2
DX = 8
der = empty("derrick", loc=(DX, 0, ROOF))
mb = MB()
mb.box((0, 0, 0.4), (3, 3, 0.8))
d_base = part("d_base", mb, flat(RED), der)
mb = MB()
for x, y in [(-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)]:
    mb.beam((x, y, 0.8), (x, y, 11), 0.2)
for z in range(1, 11, 2):
    mb.beam((-0.4, -0.4, z), (0.4, 0.4, z + 1), 0.07)
d_mast = part("d_mast", mb, flat(RED), der)
mb = MB()
for y in (-0.3, 0.3):
    mb.beam((0, y, 11), (11, y, 21), 0.22)
for k in range(1, 8):
    x = k * 11 / 8
    mb.beam((x, -0.3, 11 + x * 10 / 11), (x + 1, 0.3, 11 + (x + 1) * 10 / 11), 0.06)
d_boom = part("d_boom", mb, flat(RED), der)
hook_f = a9 + 4
dlist = [d_base, d_mast, d_boom]
HOOK_TOP = 30 + 1.8  # crane jib height above the roof
set_hook(G, hook_f, DX, 6)
for i, p_ in enumerate(dlist):
    t0 = hook_f + 4 + i * 22
    key(p_, "location", t0 - 1, (0, 0, 22))
    key(p_, "location", t0 + 18, (0, 0, 0))
    set_hook(G, t0, None, 8)
    set_hook(G, t0 + 18, None, HOOK_TOP - 2)
    set_hook(G, t0 + 21, None, 8)
    pop(p_, t0 - 3, 2)


def lower(o, t0, dur, base, dx, up=1.5, drop=H + 30):
    """Sling a part sideways off the roof edge and lower it to the street."""
    bx, by, bz = base
    key(o, "location", t0, (bx, by, bz))
    key(o, "location", t0 + dur * 0.3, (bx + dx, by, bz + up))
    key(o, "location", t0 + dur, (bx + dx, by, bz - drop))


t0 = W("derrick", "dismantles")
dur = 24
step_ = (b9 - t0 - dur) / 6
lower(G["jib"], t0, dur, (0, 0, 0), 14)
lower(G["cj"], t0 + step_, dur, (0, 0, 0), 26)
lower(G["head"], t0 + step_ * 2, dur, (0, 0, 0), 18)
for i, s in enumerate(reversed(G["secs"])):
    lower(s, t0 + step_ * (3 + i * 0.6), dur, (0, 0, (4 - i) * 6), 18)
shot(a9, b9, (0, (30, -46, ROOF + 22), (4, 0, ROOF + 14)), (1, (34, -50, ROOF + 18), (8, 0, ROOF + 6)))

# the derrick is stranded; a smaller crane deals with it, then a smaller one still
M = make_crane("M", 2, col_=(0.15, 0.45, 0.8), s=0.45, jib=16, cj=6, loc=(-4, -6, ROOF))
tiny = make_crane("Tiny", 1, col_=YELLOW, s=0.22, jib=9, cj=3, loc=(-5, -8, ROOF))
s0 = W("smaller", "so")
pop(M["root"], s0, 8, (0.45,) * 3)
s1 = s0 + 16
lower(d_boom, s1, 18, (0, 0, 0), 14)
lower(d_mast, s1 + 12, 18, (0, 0, 0), 14)
lower(d_base, s1 + 24, 18, (0, 0, 0), 14)
s2 = W("smaller", "and")
pop(tiny["root"], s2, 8, (0.22,) * 3)
for i, p_ in enumerate([M["jib"], M["cj"], M["head"]]):
    lower(p_, s2 + 10 + i * 10, 16, (0, 0, 0), 18, drop=60)
for i, p_ in enumerate(M["secs"]):
    lower(p_, s2 + 34 + i * 8, 14, (0, 0, (1 - i) * 6), 24, drop=60)
vis(der, (a9, b10))
vis(M["root"], (s0, b10))
vis(tiny["root"], (s2, b10))

# the lift, on the roof
lift = empty("lift", loc=(-5, 2.5, ROOF))
W_ = 4.0
CL = (0.75, 0.75, 0.73)
boxpart("l_back", (0, 3, 2.25), (W_, 0.2, 4.5), CL, lift)
boxpart("l_l", (-W_ / 2, 1.5, 2.25), (0.2, 3, 4.5), CL, lift)
boxpart("l_r", (W_ / 2, 1.5, 2.25), (0.2, 3, 4.5), CL, lift)
boxpart("l_top", (0, 1.5, 4.6), (W_ + 0.2, 3.2, 0.2), CL, lift)
mb = MB()
mb.box((0, 2.85, 2.2), (W_ - 0.4, 0.1, 4.0))
part("l_glow", mb, glow((1.0, 0.85, 0.6), 1.5), lift)
d1 = boxpart("door1", (0, 0, 2.2), (W_ / 2, 0.12, 4.2), STEEL, lift, (-W_ / 2 - 0.9, -0.05, 0))
d2 = boxpart("door2", (0, 0, 2.2), (W_ / 2, 0.12, 4.2), STEEL, lift, (W_ / 2 + 0.9, -0.05, 0))
walk = W("smaller", "last")
shut = walk + 36
key(tiny["root"], "location", walk, (-5, -8, ROOF))
key(tiny["root"], "location", shut - 2, (-5, 3.8, ROOF))
for d_, sg in ((d1, -1), (d2, 1)):
    key(d_, "location", shut - 1, (sg * (W_ / 2 + 0.9), -0.05, 0))
    key(d_, "location", shut + 12, (sg * W_ / 4, -0.05, 0))
vis(lift, (a8, LAST))
shot(a10, walk - 1, (0, (24, -40, ROOF + 12), (0, -2, ROOF + 5)), (1, (20, -38, ROOF + 10), (-2, -2, ROOF + 4)))
shot(walk, b10, (0, (-3, -21, ROOF + 4), (-5, 0, ROOF + 1.6)), (1, (-4, -18, ROOF + 3.4), (-5, 2, ROOF + 2)))

# ================================================================ 11. END
X = make_crane("X", 8, jib=34, loc=(-40, -22, 0))
set_hook(X, a11, 18, 14)
pop(X["cab"], W("end", "cab"), 8)
pop(X["hook"], W("end", "hook"), 8)
climber = boxpart("climber", (0, 0, 1), (1.0, 0.7, 2), (0.9, 0.25, 0.08), X["root"], (0, -1.45, 0))
cl0 = W("end", "someone")
key(climber, "location", cl0, (0, -1.45, 26))
key(climber, "location", W("end", "congrat") - 2, (0, -1.45, 46))
vis(X["root"], (a11, LAST))
con = W("end", "congrat")
shot(a11, con - 1, (0, (-14, -38, 44), (-38, -22, 46)), (1, (-16, -40, 50), (-38, -22, 48)))
shot(con, LAST, (0, (-34, -94, 34), (-30, -10, 46)), (1, (10, -210, 58), (-14, 0, 68)))

# dawn for the driver's climb
for f, sky, sn, hz in [(a11 - 1, (1, 1, 1, 1), (1, 1, 1), hz_color),
                       (a11 + 2, (1.25, 0.82, 0.65, 1), (1.0, 0.72, 0.5), (0.95, 0.72, 0.62, 1)),
                       (con, (1.25, 0.82, 0.65, 1), (1.0, 0.72, 0.5), (0.95, 0.72, 0.62, 1)),
                       (con + 45, (1.05, 0.95, 0.88, 1), (1.0, 0.9, 0.78), (0.82, 0.78, 0.82, 1))]:
    tint.outputs[0].default_value = sky
    tint.outputs[0].keyframe_insert("default_value", frame=f)
    sun_d.color = sn
    sun_d.keyframe_insert("color", frame=f)
    for rgb in HAZE_RGBS:
        rgb.outputs[0].default_value = hz
        rgb.outputs[0].keyframe_insert("default_value", frame=f)

apply_vis()

# ---------------------------------------------------------------- render settings
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.eevee.taa_render_samples = 16
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = LAST
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 95
scene.render.filepath = os.path.join(HERE, "frames", "f")
scene.render.use_overwrite = False
scene.render.use_placeholder = True

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "crane.blend"))
print(f"BUILD OK frames={LAST} beats=" + str({n: B(n) for n in ORDER}))

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv and argv[0] == "preview":
    import time
    scene.render.resolution_percentage = 40
    scene.render.use_overwrite = True
    scene.render.use_placeholder = False
    for f in argv[1:]:
        t = time.time()
        scene.frame_set(int(f))
        scene.render.filepath = os.path.join(HERE, "preview", f"p{int(f):05d}.jpg")
        bpy.ops.render.render(write_still=True)
        print(f"PREVIEW {f} {time.time() - t:.1f}s")
