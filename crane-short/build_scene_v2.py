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
from mathutils import Matrix, Vector

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


# facade tiles of 4x4 windows; alpha 1 = wall (takes the building tint), alpha 0 = glass
import numpy as np

S_ = 512


def facade_image(name, curtain=False):
    rng = np.random.default_rng(11 if curtain else 5)
    a = np.ones((S_, S_, 4), dtype=np.float32)
    cell = S_ // 4
    a[..., :3] *= 0.92 + 0.08 * rng.random((S_, S_, 1)).astype(np.float32)
    a[::cell // 4, :, :3] *= 0.9  # faint coursing lines
    for iy in range(4):
        for ix in range(4):
            y, x = iy * cell, ix * cell
            if curtain:
                g = rng.uniform(0.75, 1.15)
                a[y:y + cell, x:x + cell, :3] = np.array((0.13, 0.26, 0.4)) * g
                a[y:y + cell, x:x + cell, 3] = 0
                a[y:y + cell // 6, x:x + cell, :3] = (0.015, 0.018, 0.024)
                a[y:y + cell, x:x + 5, :3] = (0.015, 0.018, 0.024)
                continue
            r = rng.random()
            c = (0.8, 0.56, 0.3) if r < 0.06 else (0.05, 0.08, 0.13) if r < 0.6 else (0.1, 0.17, 0.27)
            t, b, l, w = y + 22, y + cell - 18, x + 24, cell - 48
            a[t - 7:b + 7, l - 7:l + w + 7, :3] = (0.86, 0.85, 0.82)        # frame
            a[t - 13:t - 7, l - 13:l + w + 13, :3] = (0.5, 0.5, 0.5)        # sill shadow
            a[t:b, l:l + w, :3] = c
            a[t:b, l:l + w, 3] = 0
            if rng.random() < 0.3:
                a[b - (b - t) // 3:b, l:l + w, :3] = (0.8, 0.77, 0.7)       # blind
            a[t:b, l + w // 2 - 2:l + w // 2 + 2, :3] = (0.8, 0.8, 0.78)    # mullion
    img = bpy.data.images.new(name, S_, S_, alpha=True)
    img.alpha_mode = "CHANNEL_PACKED"
    img.pixels.foreach_set(a.ravel())
    img.pack()
    return img


def building_mat(name, img, tinted, glass_rough=0.1, wall_rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    base = tex.outputs["Color"]
    if tinted:
        attr = nt.nodes.new("ShaderNodeAttribute")
        attr.attribute_name = "tint"
        noi = nt.nodes.new("ShaderNodeTexNoise")
        noi.inputs["Scale"].default_value = 0.35
        noi.inputs["Detail"].default_value = 5
        co = nt.nodes.new("ShaderNodeNewGeometry")
        nt.links.new(co.outputs["Position"], noi.inputs["Vector"])
        grime = nt.nodes.new("ShaderNodeMapRange")
        grime.inputs["From Min"].default_value = 0.3
        grime.inputs["From Max"].default_value = 0.7
        grime.inputs["To Min"].default_value = 0.72
        nt.links.new(noi.outputs[0], grime.inputs["Value"])
        m1 = nt.nodes.new("ShaderNodeMixRGB")
        m1.blend_type = "MULTIPLY"
        m1.inputs[0].default_value = 1
        nt.links.new(tex.outputs["Color"], m1.inputs[1])
        nt.links.new(attr.outputs[0], m1.inputs[2])
        m2 = nt.nodes.new("ShaderNodeMixRGB")
        m2.blend_type = "MULTIPLY"
        nt.links.new(grime.outputs[0], m2.inputs[0])
        m2.inputs[0].default_value = 1
        nt.links.new(m1.outputs[0], m2.inputs[1])
        gc = nt.nodes.new("ShaderNodeCombineColor")
        nt.links.new(grime.outputs[0], gc.inputs[0])
        nt.links.new(grime.outputs[0], gc.inputs[1])
        nt.links.new(grime.outputs[0], gc.inputs[2])
        nt.links.new(gc.outputs[0], m2.inputs[2])
        m2.inputs[0].default_value = 1
        m3 = nt.nodes.new("ShaderNodeMixRGB")
        nt.links.new(tex.outputs["Alpha"], m3.inputs[0])
        nt.links.new(tex.outputs["Color"], m3.inputs[1])
        nt.links.new(m2.outputs[0], m3.inputs[2])
        base = m3.outputs[0]
    finish_mat(m, base)
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = glass_rough
    rr.inputs["To Max"].default_value = wall_rough
    nt.links.new(tex.outputs["Alpha"], rr.inputs["Value"])
    bs = nt.nodes["Principled BSDF"]
    nt.links.new(rr.outputs[0], bs.inputs["Roughness"])
    bs.inputs["Metallic"].default_value = metal
    return m


wall_mat = building_mat("wall", facade_image("facade"), True)
curtain_mat = building_mat("curtain", facade_image("curtain", True), False, 0.07, 0.07, 0.35)


def proc(name, c1, c2, scale=1.5, rough=0.9, bump=0.5):
    """Noisy two-colour surface for dirt, concrete and asphalt."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    noi = nt.nodes.new("ShaderNodeTexNoise")
    noi.inputs["Scale"].default_value = scale
    noi.inputs["Detail"].default_value = 8
    noi.inputs["Roughness"].default_value = 0.6
    nt.links.new(geo.outputs["Position"], noi.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB")
    rp.color_ramp.elements[0].position = 0.34
    rp.color_ramp.elements[1].position = 0.66
    rp.color_ramp.elements[0].color = (*c1, 1)
    rp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(noi.outputs[0], rp.inputs[0])
    finish_mat(m, rp.outputs[0], rough)
    bm = nt.nodes.new("ShaderNodeBump")
    bm.inputs["Strength"].default_value = bump
    nt.links.new(noi.outputs[0], bm.inputs["Height"])
    nt.links.new(bm.outputs[0], nt.nodes["Principled BSDF"].inputs["Normal"])
    return m


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
        self.cur = (1, 1, 1)

    def add(self, verts, faces, col=None, mat=0, uvs=None):
        col = col or self.cur
        s = len(self.v)
        self.v += [tuple(p) for p in verts]
        for i, fc in enumerate(faces):
            self.f.append([s + j for j in fc])
            self.uv.append(uvs[i] if uvs else [(0, 0)] * len(fc))
            self.col.append(col)
            self.mi.append(mat)

    def box(self, c, s, col=None, tile=None, wall=0):
        """Axis-aligned box. tile=metres per window gives facade UVs; the top uses slot 1."""
        x, y, z = c
        a, b, h = s[0] / 2, s[1] / 2, s[2] / 2
        vs = [(x - a, y - b, z - h), (x + a, y - b, z - h), (x + a, y + b, z - h), (x - a, y + b, z - h),
              (x - a, y - b, z + h), (x + a, y - b, z + h), (x + a, y + b, z + h), (x - a, y + b, z + h)]
        sides = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        cap = [(3, 2, 1, 0), (4, 5, 6, 7)]
        if tile:
            for i, fc in enumerate(sides):
                u = (round((s[0] if i % 2 == 0 else s[1]) / tile) or 1) / 4
                v = (round(s[2] / tile) or 1) / 4
                self.add(vs, [fc], col, wall, [[(0, 0), (u, 0), (u, v), (0, v)]])
            self.add(vs, cap, col, 1)
        else:
            self.add(vs, sides + cap, col, wall)

    def beam(self, p, q, t=0.12, col=None):
        p, q = Vector(p), Vector(q)
        d = (q - p).normalized()
        u = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized() * t / 2
        w = d.cross(u).normalized() * t / 2
        vs = [p - u - w, p + u - w, p + u + w, p - u + w, q - u - w, q + u - w, q + u + w, q - u + w]
        self.add(vs, [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (3, 2, 1, 0), (4, 5, 6, 7)], col)

    def ball(self, c, r, col=None, sz=1.0, rows=7, cols=10):
        vs = [(c[0], c[1], c[2] + r * sz)]
        for a in range(1, rows):
            th = math.pi * a / rows
            for b in range(cols):
                ph = 2 * math.pi * b / cols
                vs.append((c[0] + r * math.sin(th) * math.cos(ph), c[1] + r * math.sin(th) * math.sin(ph), c[2] + r * sz * math.cos(th)))
        vs.append((c[0], c[1], c[2] - r * sz))
        fs = []
        for b in range(cols):
            fs.append((0, 1 + b, 1 + (b + 1) % cols))
            fs.append((len(vs) - 1, 1 + (rows - 2) * cols + (b + 1) % cols, 1 + (rows - 2) * cols + b))
        for a in range(rows - 2):
            for b in range(cols):
                p = 1 + a * cols
                fs.append((p + b, p + cols + b, p + cols + (b + 1) % cols, p + (b + 1) % cols))
        self.add(vs, fs, col)

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


def tpart(name, mb, parent=None, loc=(0, 0, 0)):
    """Multi-coloured part: colours come from the mesh's tint attribute."""
    return obj(name, mb.mesh(name), [roof_mat], parent, loc)


def smooth(o):
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    o.data.update()
    return o


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


NEONS, HILITES = [], []


def neon(o, a, b, thick=0.05, power=5.0):
    """Wrap an object in a pulsing neon-orange shell between frames a and b."""
    c = obj(o.name + "_neon", o.data, (), o)
    m = bpy.data.materials.new(o.name + "_neon")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out_ = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*NEON, 1)  # stays orange when clipped
    nt.links.new(em.outputs[0], out_.inputs[0])
    for sl in c.material_slots:
        sl.link = "OBJECT"
        sl.material = m
    wf = c.modifiers.new("tubes", "WIREFRAME")   # glowing tubes along the edges
    wf.thickness = thick
    wf.use_even_offset = True
    wf.offset = 1
    st = em.inputs[1]
    # tube strike: a quick flicker, then a slow breathing glow
    for f_, k in [(a, 0.0), (a + 2, 1.0), (a + 4, 0.15), (a + 6, 0.9), (a + 8, 0.3), (a + 11, 1.0)]:
        st.default_value = power * k
        st.keyframe_insert("default_value", frame=f_)
    f_ = a + 26
    up = False
    while f_ < b - 6:
        st.default_value = power * (1.0 if up else 0.6)
        st.keyframe_insert("default_value", frame=f_)
        up = not up
        f_ += 15
    st.default_value = power * 0.8
    st.keyframe_insert("default_value", frame=b - 4)
    st.default_value = 0
    st.keyframe_insert("default_value", frame=b)
    NEONS.append((c, a, b))
    HILITES.append((a, b))
    return c


def apply_vis():
    def walk(o):
        yield o
        for c in o.children:
            yield from walk(c)

    neon_set = {n[0] for n in NEONS}
    for c, a, b in NEONS:
        c.hide_render = True
        c.keyframe_insert("hide_render", frame=1)
        c.hide_render = False
        c.keyframe_insert("hide_render", frame=a)
        c.hide_render = True
        c.keyframe_insert("hide_render", frame=b + 1)
    for root, ranges in VIS:
        for o in walk(root):
            if o in neon_set:
                continue
            o.hide_render = True
            o.keyframe_insert("hide_render", frame=1)
            for a, b in ranges:
                o.hide_render = False
                o.keyframe_insert("hide_render", frame=a)
                o.hide_render = True
                o.keyframe_insert("hide_render", frame=b + 1)


ORANGE = (0.95, 0.23, 0.012)
BLACK = (0.014, 0.014, 0.017)
NEON = (1.0, 0.1, 0.004)
WHITE = (0.92, 0.92, 0.92)
DARK = (0.04, 0.05, 0.07)
STEEL = (0.25, 0.27, 0.3)
CONCRETE = (0.62, 0.62, 0.60)
SEC_DATA = {}


def section_mesh(col_):
    if col_ in SEC_DATA:
        return SEC_DATA[col_]
    mb = MB()
    mb.cur = col_
    w, h = 1.0, 6.0
    cs = [(-w, -w), (w, -w), (w, w), (-w, w)]
    for x, y in cs:
        mb.beam((x, y, 0), (x, y, h), 0.2)
    brace = BLACK if col_ != BLACK else (0.25, 0.25, 0.27)
    for z0 in (0, 3):
        for i in range(4):
            a, b = cs[i], cs[(i + 1) % 4]
            mb.beam((*a, z0), (*b, z0), 0.1)
            mb.beam((*a, z0), (*b, z0 + 3), 0.09, brace)
    for z in range(0, 12):                                   # ladder inside the mast
        zz = z * 0.5
        mb.beam((-0.25, 0.75, zz), (0.25, 0.75, zz), 0.035, (0.6, 0.6, 0.6))
    for x in (-0.25, 0.25):
        mb.beam((x, 0.75, 0), (x, 0.75, h), 0.05, (0.6, 0.6, 0.6))
    mb.box((0, -0.4, 0.05), (1.7, 1.0, 0.06), (0.1, 0.1, 0.11))  # rest platform
    me = mb.mesh("section")
    me.materials.append(roof_mat)
    SEC_DATA[col_] = me
    return me


def make_crane(name, n, col_=ORANGE, chain=False, jib=36.0, cj=12.0, s=1.0, loc=(0, 0, 0)):
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
    trim = BLACK if col_ != BLACK else ORANGE
    STEEL_L = (0.55, 0.56, 0.58)

    mb = MB()
    mb.cur = col_
    mb.box((0, 0, 0.5), (3.2, 3.2, 1.0), trim)                # slewing ring
    mb.box((0, 0, 1.15), (2.6, 2.6, 0.3), col_)
    for x, y in [(-1, -1), (1, -1), (1, 1), (-1, 1)]:
        mb.beam((x, y, 1), (0, 0, 9), 0.18)
    mb.beam((0, 0, 3), (0, 0, 9), 0.12)
    for z in (3.5, 6):
        k = (9 - z) / 8
        for (x0, y0), (x1, y1) in [((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))]:
            mb.beam((x0 * k, y0 * k, z), (x1 * k, y1 * k, z), 0.07, trim)
    mb.box((0, 0, 9.15), (0.6, 0.6, 0.3), trim)
    mb.box((-1.5, 1.9, 1.3), (1.2, 0.6, 1.0), (0.6, 0.6, 0.62))  # electrics cabinet
    head = tpart(f"{name}_head", mb, top)

    mb = MB()
    mb.box((1.3, -2.3, 1.2), (2.2, 2.2, 2.4), BLACK)
    mb.box((1.3, -2.3, 2.5), (2.4, 2.4, 0.2), ORANGE)         # roof
    mb.box((1.3, -2.3, 0.05), (2.3, 2.3, 0.15), ORANGE)
    mb.box((1.3, -3.42, 1.45), (1.9, 0.05, 1.6), (0.25, 0.42, 0.55))
    mb.box((2.42, -2.3, 1.45), (0.05, 1.9, 1.6), (0.25, 0.42, 0.55))
    mb.beam((0.4, -3.46, 1.45), (2.2, -3.46, 1.45), 0.05, BLACK)
    mb.beam((1.3, -3.46, 0.7), (1.3, -3.46, 2.2), 0.05, BLACK)
    cab = tpart(f"{name}_cab", mb, head)

    mb = MB()
    mb.cur = col_
    bays = int(jib / 3)
    L = jib / bays
    for i in range(bays):
        x0, x1 = 1 + i * L, 1 + (i + 1) * L
        for y in (-0.8, 0.8):
            mb.beam((x0, y, 1), (x1, y, 1), 0.14)
            mb.beam((x0, y, 1), (x0 + L / 2, 0, 2.5), 0.08, trim)
            mb.beam((x0 + L / 2, 0, 2.5), (x1, y, 1), 0.08, trim)
        mb.beam((x0 + L / 2, 0, 2.5), (x1 + L / 2 if i < bays - 1 else x1, 0, 2.5), 0.14)
        mb.beam((x0, -0.8, 1), (x0, 0.8, 1), 0.08, trim)
        mb.beam((x0, -1.2, 1.0), (x1, -1.2, 1.0), 0.05, STEEL_L)      # walkway
        mb.beam((x0, -1.2, 1.9), (x1, -1.2, 1.9), 0.035, STEEL_L)     # handrail
        mb.beam((x0, -1.2, 1.0), (x0, -1.2, 1.9), 0.035, STEEL_L)
        mb.beam((x0, -1.2, 1.0), (x0, -0.8, 1.0), 0.05, STEEL_L)
    mb.beam((0, 0, 9), (jib * 0.65, 0, 2.6), 0.07, DARK)
    mb.beam((0, 0, 9), (jib * 0.35, 0, 2.6), 0.07, DARK)
    mb.box((jib + 1, 0, 1.6), (0.5, 1.8, 1.4), trim)
    jib_o = tpart(f"{name}_jib", mb, top)

    mb = MB()
    mb.cur = col_
    mb.box((-cj / 2 - 1, 0, 1.0), (cj, 2.4, 0.3))
    mb.box((-cj + 4.5, 0, 1.75), (2.2, 1.6, 1.2), BLACK)      # hoist winch
    mb.box((-cj + 4.5, 0, 2.5), (1.2, 1.2, 0.5), (0.55, 0.56, 0.58))
    for y in (-1.3, 1.3):
        mb.beam((-cj - 1, y, 1.9), (-1, y, 1.9), 0.05, (0.55, 0.56, 0.58))
    mb.beam((0, 0, 9), (-cj, 0, 1.2), 0.07, DARK)
    cj_o = tpart(f"{name}_cj", mb, top)
    weights = []
    for i in range(4):
        mb = MB()
        mb.box((0, 0, 0), (2.4, 2.4, 1.15), CONCRETE)
        for k in range(4):                                     # hazard band
            mb.box((-0.9 + k * 0.6, -1.22, 0), (0.6, 0.05, 0.5), BLACK if k % 2 else ORANGE)
        weights.append(tpart(f"{name}_w{i}", mb, cj_o, (-cj + 1.5, 0, 1.75 + 1.25 * i)))

    mb = MB()
    mb.box((0, 0, 0), (1.6, 1.6, 0.4), BLACK)
    for x in (-0.7, 0.7):
        for y in (-0.9, 0.9):
            mb.box((x, y, 0.15), (0.4, 0.12, 0.4), (0.5, 0.5, 0.52))
    trolley = tpart(f"{name}_trolley", mb, jib_o, (10, 0, 0.8))
    mb = MB()
    for y in (-0.14, 0.14):
        mb.beam((0, y, 0), (0, y, -1), 0.05, DARK)
    cable = tpart(f"{name}_cable", mb, trolley)
    mb = MB()
    mb.box((0, 0, 0.1), (0.9, 0.5, 1.0), ORANGE)
    mb.box((0, 0, 0.1), (0.5, 0.56, 0.5), BLACK)
    for k in range(9):                                         # the hook itself
        a0, a1 = -2.6 + k * 0.55, -2.6 + (k + 1) * 0.55
        mb.beam((0.3 * math.cos(a0), 0, -0.9 + 0.3 * math.sin(a0)), (0.3 * math.cos(a1), 0, -0.9 + 0.3 * math.sin(a1)), 0.1, (0.15, 0.15, 0.17))
    mb.beam((0, 0, -0.4), (0, 0, -0.6), 0.14, (0.15, 0.15, 0.17))
    hook = tpart(f"{name}_hook", mb, trolley, (0, 0, -8))
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
        mb.cur = CONCRETE
        for sx in (-1, 1):                                     # orange safety barrier
            mb.beam((sx * (w / 2 - 0.1), -w / 2, 1.0), (sx * (w / 2 - 0.1), w / 2, 1.0), 0.07, ORANGE)
            mb.beam((-w / 2, sx * (w / 2 - 0.1), 1.0), (w / 2, sx * (w / 2 - 0.1), 1.0), 0.07, ORANGE)
            mb.beam((sx * (w / 2 - 0.1), -w / 2, 0.55), (sx * (w / 2 - 0.1), w / 2, 0.55), 0.05, BLACK)
            mb.beam((-w / 2, sx * (w / 2 - 0.1), 0.55), (w / 2, sx * (w / 2 - 0.1), 0.55), 0.05, BLACK)
        for k in range(8):
            q = -w / 2 + k * w / 7
            for sx in (-1, 1):
                mb.beam((sx * (w / 2 - 0.1), q, 0), (sx * (w / 2 - 0.1), q, 1.0), 0.06, BLACK)
                mb.beam((q, sx * (w / 2 - 0.1), 0), (q, sx * (w / 2 - 0.1), 1.0), 0.06, BLACK)
        for k in range(3):                                     # stacked formwork and props
            mb.box((w / 2 - 2.5, -w / 2 + 2.5 + k * 1.0, 0.35 + 0.12), (2.2, 0.8, 0.24), (0.55, 0.38, 0.2))
        floors.append(tpart(f"{name}_{i}", mb, root, (0, 0, (i + 1) * fh)))
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
        tower_type = h > 70 and random.random() < 0.45
        if tower_type:
            hue = (0.3, 0.4, 0.5)
        mb.box((x, y, h / 2), (w, d, h), hue, tile=3.6, wall=2 if tower_type else 0)
        mb.box((x, y, h + 0.25), (w, d, 0.5), random.choice(ROOFS), wall=1)
        if r < 700:
            pc = (hue[0] * 0.7, hue[1] * 0.7, hue[2] * 0.7)
            for sx in (-1, 1):                                 # parapet
                mb.box((x + sx * w / 2, y, h + 0.8), (0.5, d + 0.5, 1.6), pc, wall=1)
                mb.box((x, y + sx * d / 2, h + 0.8), (w + 0.5, 0.5, 1.6), pc, wall=1)
            for _ in range(random.randint(1, 3)):              # plant and tanks on the roof
                ux, uy = random.uniform(-w / 3, w / 3), random.uniform(-d / 3, d / 3)
                mb.box((x + ux, y + uy, h + 1.3), (random.uniform(2, 5), random.uniform(2, 5), random.uniform(1.6, 3)), (0.5, 0.5, 0.52), wall=1)
        if r < 420:
            shop = random.choice([(0.03, 0.03, 0.04), (0.2, 0.2, 0.22), (0.45, 0.42, 0.38)])
            mb.box((x, y, 2.4), (w + 0.5, d + 0.5, 4.8), shop, wall=1)   # shopfronts
            mb.box((x, y - d / 2 - 0.9, 4.7), (w * 0.8, 1.8, 0.3), ORANGE if random.random() < 0.25 else (0.2, 0.2, 0.22), wall=1)
            for lv in range(1, int(h // 14) + 1):              # cornice bands
                mb.box((x, y, lv * 14), (w + 0.7, d + 0.7, 0.45), hue, wall=1)

# the street of houses in the foreground
for i in range(-5, 6):
    x, y = i * 15.5 + 4, -72
    w, d, h = 13.5, 12, random.uniform(9, 13)
    hue = random.choice(PASTELS)
    mb.box((x, y, h / 2), (w, d, h), hue, tile=3.2)
    mb.box((x - 2, y - d / 2 - 0.06, 1.3), (1.6, 0.12, 2.6), (0.08, 0.06, 0.05), wall=1)   # door
    mb.box((x, y - d / 2 - 0.4, 2.9), (w, 0.8, 0.2), (0.9, 0.9, 0.88), wall=1)
    mb.box((x + 3.5, y + 2, h + 4), (1.2, 1.2, 3), (0.5, 0.3, 0.25), wall=1)               # chimney
    rc = (0.85, 0.42, 0.25) if i % 2 else (0.5, 0.5, 0.53)
    vs = [(x - w / 2, y - d / 2, h), (x + w / 2, y - d / 2, h), (x + w / 2, y + d / 2, h), (x - w / 2, y + d / 2, h),
          (x - w / 2, y, h + 4.5), (x + w / 2, y, h + 4.5)]
    mb.add(vs, [(0, 1, 5, 4), (2, 3, 4, 5)], rc, 1)
    mb.add(vs, [(1, 2, 5), (3, 0, 4)], hue, 1)
city = obj("city", mb.mesh("city"), [wall_mat, roof_mat, curtain_mat])

mb = MB()
mb.box((0, 0, -0.5), (6000, 6000, 1))
part("ground", mb, proc("asphalt0", (0.16, 0.16, 0.18), (0.27, 0.27, 0.29), 0.25, 0.9, 0.2))
mb = MB()
mb.box((0, -52, 0.04), (420, 18, 0.08))
part("road", mb, proc("asphalt", (0.05, 0.05, 0.06), (0.1, 0.1, 0.11), 3, 0.85, 0.3))
mb = MB()
mb.box((0, 0, 0.06), (84, 70, 0.12))
part("site", mb, proc("dirt", (0.13, 0.075, 0.04), (0.33, 0.21, 0.12), 0.9, 1.0, 1.0))


LEAF_MAT = proc("leaf", (0.03, 0.17, 0.03), (0.2, 0.48, 0.09), 2.2, 0.75, 1.5)


def ball(mb_f, c, r):
    mb_f.ball(c, r)


def tree(mb_t, mb_f, x, y, s):
    mb_t.box((x, y, 2 * s), (0.5 * s, 0.5 * s, 4 * s))
    for dx, dy, dz, r in [(0, 0, 5, 2.4), (1.5, 0.5, 4.2, 1.6), (-1.4, -0.6, 4.4, 1.7), (0.2, 1.2, 6, 1.5),
                          (-0.8, 1, 5.6, 1.4), (1, -1, 5.5, 1.3), (0, -1.4, 4.5, 1.3)]:
        ball(mb_f, (x + dx * s, y + dy * s, dz * s), r * s)


trunks, leaves = MB(), MB()
for i in range(-5, 6):
    tree(trunks, leaves, i * 15.5 + 12, -61, 1.5)
TRUNK, LEAF = (0.22, 0.13, 0.07), (0.16, 0.5, 0.14)
part("trees_t", trunks, flat(TRUNK))
tr_leaf = part("trees_f", leaves, LEAF_MAT)
tr_leaf.data.polygons.foreach_set("use_smooth", [True] * len(tr_leaf.data.polygons))
tr_leaf.data.update()

# ---------------------------------------------------------------- light, world, camera
sun_d = bpy.data.lights.new("sun", "SUN")
sun_d.energy = 2.1
sun_d.angle = math.radians(1.2)
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
dim_v = nt.nodes.new("ShaderNodeValue")
dim_m = nt.nodes.new("ShaderNodeMath")
dim_m.operation = "MULTIPLY"
nt.links.new(bs_mix.outputs[0], dim_m.inputs[0])
nt.links.new(dim_v.outputs[0], dim_m.inputs[1])
nt.links.new(dim_m.outputs[0], bg.inputs[1])
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


# ---------------------------------------------------------------- street and site dressing
mb = MB()
mb.box((0, -42.1, 0.12), (420, 2.2, 0.24), (0.42, 0.42, 0.4))      # kerbs and pavements
mb.box((0, -62, 0.12), (420, 2.2, 0.24), (0.42, 0.42, 0.4))
for i in range(-22, 23):
    mb.box((i * 9, -52, 0.09), (4.5, 0.25, 0.02), (0.85, 0.85, 0.8))
    if i % 4 == 0 and abs(i * 9) > 60:                             # street lamps
        mb.beam((i * 9, -42, 0), (i * 9, -42, 7), 0.16, (0.05, 0.05, 0.06))
        mb.beam((i * 9, -42, 7), (i * 9, -44, 7.4), 0.1, (0.05, 0.05, 0.06))
        mb.box((i * 9, -44.2, 7.35), (0.5, 0.9, 0.14), (0.8, 0.8, 0.7))

CAR_COLS = [(0.8, 0.8, 0.8), (0.03, 0.03, 0.04), (0.45, 0.05, 0.03), (0.1, 0.18, 0.32), (0.5, 0.5, 0.52)]


def car(mb_, x, y, c, along=1):
    mb_.box((x, y, 0.8), (4.3, 1.8, 0.75), c)
    mb_.box((x - 0.2, y, 1.45), (2.3, 1.6, 0.6), (0.05, 0.08, 0.11))
    mb_.box((x - 0.2, y, 1.78), (2.1, 1.5, 0.07), c)
    for dx in (-1.35, 1.35):
        for dy in (-0.92, 0.92):
            mb_.box((x + dx, y + dy, 0.36), (0.7, 0.24, 0.7), (0.02, 0.02, 0.02))
    mb_.box((x + 2.16 * along, y - 0.6, 0.85), (0.05, 0.4, 0.2), (0.95, 0.95, 0.8))
    mb_.box((x + 2.16 * along, y + 0.6, 0.85), (0.05, 0.4, 0.2), (0.95, 0.95, 0.8))
    mb_.box((x - 2.16 * along, y - 0.6, 0.85), (0.05, 0.4, 0.2), (0.6, 0.03, 0.02))
    mb_.box((x - 2.16 * along, y + 0.6, 0.85), (0.05, 0.4, 0.2), (0.6, 0.03, 0.02))


for x in (-96, -70, -38, -9, 30, 58, 90, 120):
    car(mb, x, -44.6, random.choice(CAR_COLS))

# hoarding: black panels with an orange band, open at the front so the crew stays visible
for a_, b_ in [((-42, 35), (42, 35)), ((-42, -35), (-42, 35)), ((42, -35), (42, 35))]:
    d_ = Vector(b_) - Vector(a_)
    n_ = int(d_.length / 4)
    for k in range(n_):
        p_ = Vector(a_) + d_ * ((k + 0.5) / n_)
        sz = (4.0 if abs(d_.x) > 0 else 0.15, 0.15 if abs(d_.x) > 0 else 4.0, 2.6)
        mb.box((p_.x, p_.y, 1.3), sz, BLACK)
        mb.box((p_.x, p_.y - 0.02 if abs(d_.x) else p_.y, 2.1), (sz[0] + 0.02, sz[1] + 0.04, 0.45), ORANGE)
for x in range(-26, 43, 4):                                         # front is open mesh fencing, with a site gate at the left
    mb.beam((x, -35, 0), (x, -35, 2.1), 0.07, (0.3, 0.3, 0.32))
    mb.beam((x, -35, 2.1), (min(x + 4, 42), -35, 2.1), 0.05, (0.3, 0.3, 0.32))
    mb.beam((x, -35, 1.0), (min(x + 4, 42), -35, 1.0), 0.03, (0.3, 0.3, 0.32))
    mb.box((x, -35, 0.08), (0.5, 0.5, 0.16), ORANGE)

dressing = tpart("dressing", mb)
# crane base pad with hazard edge, poured only once the tower arrives
mb = MB()
mb.box((0, 0, 0.3), (9, 9, 0.6), CONCRETE)
for k in range(9):
    q = -4.5 + k + 0.5
    c = ORANGE if k % 2 else BLACK
    mb.box((q, -4.52, 0.3), (1, 0.05, 0.6), c)
    mb.box((-4.52, q, 0.3), (0.05, 1, 0.6), c)
pad = tpart("pad", mb)
vis(pad, (B("jib")[0], B("wind")[1]))

# site cabins
mb = MB()
for x, y, z in [(-33, 22, 1.4), (-33, 10, 1.4), (-33, 22, 4.2)]:
    mb.box((x, y, z), (6, 11, 2.8), BLACK if z < 3 else ORANGE)
    for k in range(11):
        mb.box((x + 3.02, y - 5 + k, z), (0.05, 0.3, 2.6), (0.05, 0.05, 0.06) if z < 3 else (0.7, 0.16, 0.01))
    mb.box((x + 3.03, y, z + 0.1), (0.05, 2.4, 1.2), (0.25, 0.42, 0.55))
# timber stacks, pallets and pipes
for sx, sy in [(30, -26), (33, -18)]:
    for lv in range(4):
        for k in range(6):
            mb.box((sx, sy + k * 0.42, 0.14 + lv * 0.26), (6, 0.34, 0.2), (0.55 - lv * 0.02, 0.38, 0.2))
for k in range(9):
    mb.beam((20 + k * 0.28, 26, 0.2 + 0.25 * (k % 3)), (31 + k * 0.28, 26, 0.2 + 0.25 * (k % 3)), 0.22, (0.14, 0.14, 0.16))
# site vehicles and tyre tracks
mb.box((30, 16, 1.2), (8, 2.7, 1.0), ORANGE)
mb.box((27.2, 16, 2.6), (2.2, 2.5, 1.9), BLACK)
mb.box((31.5, 16, 2.4), (4.8, 2.6, 1.3), (0.14, 0.14, 0.16))
for dx in (-3, 0, 3):
    for dy in (-1.3, 1.3):
        mb.box((30 + dx, 16 + dy, 0.55), (1.1, 0.4, 1.1), (0.02, 0.02, 0.02))
for y0 in (-8, -11, 15, 18):
    mb.box((3, y0, 0.14), (70, 0.8, 0.03), (0.09, 0.055, 0.03))
# cones along the fence
for x in (-30, -22, -14, 14, 22, 30):
    mb.box((x, -32, 0.05), (0.5, 0.5, 0.1), BLACK)
    mb.beam((x, -32, 0.1), (x, -32, 0.8), 0.28, ORANGE)
dressing2 = tpart("dressing2", mb)
mb = MB()
for cx, cy, r_ in [(-26, 20, 5), (-21, 24, 4), (24, -6, 3.2)]:
    mb.ball((cx, cy, 0), r_, sz=0.5, rows=8, cols=14)
piles = smooth(part("piles", mb, proc("gravel", (0.3, 0.29, 0.27), (0.58, 0.56, 0.53), 18, 1.0, 1.0)))

# moving traffic keeps the street alive
for i in range(6):
    mb = MB()
    going = 1 if i % 2 else -1
    car(mb, 0, 0, CAR_COLS[i % 5], going)
    c_ = tpart(f"traffic{i}", mb)
    y_ = -49 if going > 0 else -55
    x0 = -220 * going + i * 40 * going
    key(c_, "location", 1, (x0, y_, 0))
    key(c_, "location", LAST, (x0 + going * 880, y_, 0))
    for fc in c_.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# ---------------------------------------------------------------- the crew
GLB = os.path.join(HERE, "assets", "ual", "x", "Animation Library[Standard]", "Godot", "AnimationLibrary_Godot_Standard.glb")
_before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=GLB)
for o in set(bpy.data.objects) - _before:
    if o.type == "MESH" and o.parent is None:
        bpy.data.objects.remove(o)
BASE_ARM = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name == "Rig")
BASE_MESH = next(o for o in BASE_ARM.children if o.type == "MESH")
ACT = {a.name.replace("_Rig", ""): a for a in bpy.data.actions}
for a_ in ACT.values():
    a_.use_fake_user = True
BASE_ARM.animation_data_clear()
for o in (BASE_ARM, BASE_MESH):
    col.objects.unlink(o)  # only ever used as the template for the crew

# dress the mannequin: each face takes the material of the bone that drives it
me_ = BASE_MESH.data
names = {g.index: g.name for g in BASE_MESH.vertex_groups}
dom = []
for v in me_.vertices:
    dom.append(names[max(v.groups, key=lambda g: g.weight).group] if len(v.groups) else "")
zs = [v.co.z for v in me_.vertices]
HT = max(zs)
head_vs = [v.co for v in me_.vertices if dom[v.index] in ("DEF-head",)]
HEAD_Y = min(c.y for c in head_vs)
HEAD_CX = sum(c.x for c in head_vs) / len(head_vs)
HEAD_TOP = max(c.z for c in head_vs)
HEAD_MIDZ = HEAD_TOP - (HEAD_TOP - min(c.z for c in head_vs)) * 0.42
# the outfit is painted from each vertex's T-pose position, which gives crisp clean edges
rest = me_.attributes.new("rest", "FLOAT_VECTOR", "POINT")
rest.data.foreach_set("vector", [c for v in me_.vertices for c in v.co])
bn = BASE_ARM.data.bones
Z_NECK = bn["DEF-neck"].head_local.z
Z_HIP = bn["DEF-thigh.L"].head_local.z + 0.05
X_SH = abs(bn["DEF-upper_arm.L"].head_local.x) + 0.03
X_WR = abs(bn["DEF-hand.L"].head_local.x) - 0.02
Z_ANK = bn["DEF-foot.L"].head_local.z + 0.02
NECK_R = max(abs(c.x - HEAD_CX) for c in head_vs) * 1.15
crew_mat = bpy.data.materials.new("crew")
crew_mat.use_nodes = True
nt = crew_mat.node_tree
at = nt.nodes.new("ShaderNodeAttribute")
at.attribute_name = "rest"
sp = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(at.outputs["Vector"], sp.inputs[0])
ab = nt.nodes.new("ShaderNodeMath")
ab.operation = "ABSOLUTE"
nt.links.new(sp.outputs["X"], ab.inputs[0])


def mask(lo_x, hi_x, lo_z, hi_z):
    """1 inside the given box of T-pose space."""
    out_ = None
    for sock, lim, op in ((ab.outputs[0], lo_x, "GREATER_THAN"), (ab.outputs[0], hi_x, "LESS_THAN"),
                          (sp.outputs["Z"], lo_z, "GREATER_THAN"), (sp.outputs["Z"], hi_z, "LESS_THAN")):
        m_ = nt.nodes.new("ShaderNodeMath")
        m_.operation = op
        nt.links.new(sock, m_.inputs[0])
        m_.inputs[1].default_value = lim
        if out_ is None:
            out_ = m_.outputs[0]
        else:
            t_ = nt.nodes.new("ShaderNodeMath")
            t_.operation = "MULTIPLY"
            nt.links.new(out_, t_.inputs[0])
            nt.links.new(m_.outputs[0], t_.inputs[1])
            out_ = t_.outputs[0]
    return out_


cur = nt.nodes.new("ShaderNodeRGB")
cur.outputs[0].default_value = (0.022, 0.024, 0.032, 1)   # work trousers and sleeves
cur = cur.outputs[0]
TH = Z_NECK - Z_HIP
for ms, c_ in [(mask(-1, X_SH, Z_HIP, 9), ORANGE),                                   # hi-vis vest
               (mask(-1, X_SH, Z_HIP + TH * 0.2, Z_HIP + TH * 0.27), (0.85, 0.85, 0.8)),          # reflective bands
               (mask(-1, X_SH, Z_HIP + TH * 0.56, Z_HIP + TH * 0.63), (0.85, 0.85, 0.8)),
               (mask(-1, X_SH, Z_HIP - 0.03, Z_HIP + 0.02), (0.008, 0.008, 0.008)),               # belt
               (mask(-1, 0.011, Z_HIP + TH * 0.05, Z_NECK), (0.012, 0.012, 0.012)),         # zip
               (mask(-1, NECK_R, Z_NECK + 0.035, 9), (0.6, 0.36, 0.25)),                                # head and neck
               (mask(X_WR, 9, -1, 9), (0.014, 0.014, 0.014)),                                     # gloves
               (mask(-1, 9, -1, Z_ANK), (0.03, 0.02, 0.012))]:                                    # boots
    mx = nt.nodes.new("ShaderNodeMixRGB")
    nt.links.new(ms, mx.inputs[0])
    nt.links.new(cur, mx.inputs[1])
    mx.inputs[2].default_value = (*c_, 1)
    cur = mx.outputs[0]
finish_mat(crew_mat, cur, 0.6)
me_.materials.clear()
me_.materials.append(crew_mat)
me_.polygons.foreach_set("material_index", [0] * len(me_.polygons))
HEAD_BONE = BASE_ARM.data.bones["DEF-head"]
HEAD_INV = (HEAD_BONE.matrix_local @ Matrix.Translation((0, HEAD_BONE.length, 0))).inverted()

def surf(z, half=0.03):
    """Front of the face at height z, so features sit on the skin."""
    ys = [c.y for c in head_vs if abs(c.z - z) < 0.018 and abs(c.x - HEAD_CX) < half]
    return min(ys) if ys else HEAD_Y


mb = MB()
SKIN = (0.6, 0.36, 0.25)
HEAD_CY = sum(c.y for c in head_vs) / len(head_vs)
HEAD_R = max(abs(c.x - HEAD_CX) for c in head_vs)
HEAD_RY = max(abs(c.y - HEAD_CY) for c in head_vs)
# hard hat: a dome, a ridge and a brim that is longer at the front
HZ = HEAD_TOP - 0.045
rx, ry = HEAD_R * 1.14, HEAD_RY * 1.14
rows_, cols_ = 7, 18
vs = [(HEAD_CX, HEAD_CY, HZ + 0.1)]
for a_ in range(1, rows_ + 1):
    th = (math.pi / 2) * a_ / rows_
    for b_ in range(cols_):
        ph = math.tau * b_ / cols_
        vs.append((HEAD_CX + rx * math.sin(th) * math.cos(ph), HEAD_CY + ry * math.sin(th) * math.sin(ph), HZ + 0.1 * math.cos(th)))
fs = [(0, 1 + b_, 1 + (b_ + 1) % cols_) for b_ in range(cols_)]
for a_ in range(rows_ - 1):
    p_ = 1 + a_ * cols_
    fs += [(p_ + b_, p_ + cols_ + b_, p_ + cols_ + (b_ + 1) % cols_, p_ + (b_ + 1) % cols_) for b_ in range(cols_)]
mb.add(vs, fs, ORANGE)
vs = []
for b_ in range(cols_):
    ph = math.tau * b_ / cols_
    front = 1.0 + 0.45 * max(0, -math.sin(ph)) ** 2
    vs.append((HEAD_CX + rx * math.cos(ph), HEAD_CY + ry * math.sin(ph), HZ))
    vs.append((HEAD_CX + (rx + 0.018) * math.cos(ph), HEAD_CY + (ry + 0.018) * front * math.sin(ph), HZ - 0.008))
mb.add(vs, [(2 * b_, 2 * ((b_ + 1) % cols_), 2 * ((b_ + 1) % cols_) + 1, 2 * b_ + 1) for b_ in range(cols_)], ORANGE)
mb.beam((HEAD_CX, HEAD_CY - ry, HZ + 0.015), (HEAD_CX, HEAD_CY, HZ + 0.11), 0.02, (0.6, 0.12, 0.008))
mb.beam((HEAD_CX, HEAD_CY, HZ + 0.11), (HEAD_CX, HEAD_CY + ry, HZ + 0.015), 0.02, (0.6, 0.12, 0.008))
mb.ball((HEAD_CX, surf(HEAD_MIDZ - 0.018) - 0.002, HEAD_MIDZ - 0.018), 0.017, SKIN, sz=1.0, rows=4, cols=6)      # nose
for k in range(6):                                                                               # smile
    t0, t1 = (k / 6 - 0.5) * 2, ((k + 1) / 6 - 0.5) * 2
    my = surf(HEAD_MIDZ - 0.058, 0.04)
    mb.beam((HEAD_CX + 0.036 * t0, my - 0.001 + 0.010 * t0 * t0, HEAD_MIDZ - 0.066 + 0.018 * t0 * t0),
            (HEAD_CX + 0.036 * t1, my - 0.001 + 0.010 * t1 * t1, HEAD_MIDZ - 0.066 + 0.018 * t1 * t1), 0.008, (0.2, 0.05, 0.05))
for sx in (-1, 1):                                                                               # raised brows
    by = surf(HEAD_MIDZ + 0.06, 0.05)
    mb.beam((HEAD_CX + sx * 0.02, by - 0.001, HEAD_MIDZ + 0.058), (HEAD_CX + sx * 0.058, by + 0.012, HEAD_MIDZ + 0.062), 0.011, (0.06, 0.035, 0.02))
FACE_ME = mb.mesh("face")
FACE_ME.materials.append(roof_mat)
FACE_ME.polygons.foreach_set("use_smooth", [True] * len(FACE_ME.polygons))
mb = MB()
for sx in (-1, 1):
    mb.ball((sx * 0.038, 0.012, 0), 0.021, (0.92, 0.92, 0.9), rows=6, cols=10)
    mb.ball((sx * 0.038, -0.002, 0), 0.0115, (0.008, 0.008, 0.01), rows=5, cols=8)
    mb.ball((sx * 0.041, -0.012, 0.004), 0.0032, (1, 1, 1), rows=3, cols=5)
EYES_ME = mb.mesh("eyes")
EYES_ME.materials.append(roof_mat)
EYES_ME.polygons.foreach_set("use_smooth", [True] * len(EYES_ME.polygons))

CREW = 0


def worker(parent=None, loc=(0, 0, 0), face=(0, -1), scale=1.2):
    """One crew member: their own rig instance plus a hat, a face and blinking eyes."""
    global CREW
    CREW += 1
    n_ = f"crew{CREW}"
    carrier = empty(n_, parent, loc)
    carrier.scale = (scale,) * 3
    carrier.rotation_euler = (0, 0, math.atan2(face[0], -face[1]))
    arm = BASE_ARM.copy()
    col.objects.link(arm)
    arm.parent = carrier
    arm.animation_data_create()
    me = BASE_MESH.copy()
    col.objects.link(me)
    me.parent = arm
    for md in me.modifiers:
        if md.type == "ARMATURE":
            md.object = arm
    for data, l_ in ((FACE_ME, (0, 0, 0)), (EYES_ME, (HEAD_CX, surf(HEAD_MIDZ + 0.022, 0.05), HEAD_MIDZ + 0.022))):
        o = bpy.data.objects.new(n_ + data.name, data)
        col.objects.link(o)
        o.parent = arm
        o.parent_type = "BONE"
        o.parent_bone = "DEF-head"
        o.matrix_parent_inverse = HEAD_INV
        o.location = l_
    eyes = o
    f_ = random.randint(10, 80)
    while f_ < LAST:
        key(eyes, "scale", f_, (1, 1, 1))
        key(eyes, "scale", f_ + 2, (1, 1, 0.08))
        key(eyes, "scale", f_ + 4, (1, 1, 1))
        f_ += random.randint(60, 150)
    return dict(root=carrier, arm=arm, me=me)


def acts(w, *clips):
    """Play animation clips in sequence: (clip name, first frame, last frame[, reversed])."""
    ad = w["arm"].animation_data
    for i, c in enumerate(clips):
        a_ = ACT[c[0]]
        length = max(a_.frame_range[1] - a_.frame_range[0], 1)
        tr = ad.nla_tracks.new()
        st = tr.strips.new(c[0], int(c[1]), a_)
        st.scale = 1.25                  # clips were imported at 24 fps
        st.repeat = max((c[2] - c[1]) / (length * 1.25), 0.1)
        st.use_reverse = len(c) > 3 and c[3]
        st.blend_in = 0 if i == 0 else 6
        st.extrapolation = "HOLD" if i == 0 else "HOLD_FORWARD"


def stroll(w, f0, f1, p0, p1):
    """Walk in a straight line at constant speed."""
    key(w["root"], "location", f0, p0)
    key(w["root"], "location", f1, p1)
    for fc in w["root"].animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


# pedestrians on both pavements, for the whole film
for i in range(8):
    y_ = -42.5 if i % 2 else -62.5
    d_ = 1 if i < 4 else -1
    w_ = worker(loc=(0, y_, 0.24), face=(d_, 0), scale=1.0)
    acts(w_, ("Walk_Loop", 1, LAST))
    x_ = -70 + i * 22
    stroll(w_, 1, LAST, (x_, y_, 0.24), (x_ + d_ * 110, y_, 0.24))


# ================================================================ 1. BRANCH
a, b = B("branch")
snap = W("branch", "breaks") + 4
TX = -13
tree_root = empty("tree1")
mb = MB()
mb.beam((TX, 0, 0), (TX, 0, 15), 2.0)
trunk_mat = proc("bark", (0.05, 0.03, 0.015), (0.2, 0.12, 0.07), 6, 1.0, 1.5)
part("trunk", mb, trunk_mat, tree_root)
mb = MB()
for dx, dy, dz, r in [(0, 0, 20, 8), (-6, 3, 16, 6), (-3, -5, 15, 5.5), (4, 4, 17, 6), (-5, -3, 23, 5), (3, -4, 22, 5), (-9, 0, 20, 5), (5, 2, 24, 4.5)]:
    ball(mb, (TX + dx, dy, dz), r)
crown = part("crown", mb, LEAF_MAT, tree_root)
crown.data.polygons.foreach_set("use_smooth", [True] * len(crown.data.polygons))
# the branch pivots where it meets the trunk so it can snap
branch = empty("branch", tree_root, (TX, 0, 13))
mb = MB()
mb.beam((0, 0, 0), (19, 0, 3), 0.8)
part("limb", mb, trunk_mat, branch)
mb = MB()
ball(mb, (15, 1, 5), 3)
ball(mb, (19, -1, 4.5), 2.2)
tuft = part("tuft", mb, LEAF_MAT, branch)
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
mb.beam((ROPE_X + 10.6, -3, 2.1), (ROPE_X, 0, ROPE_TOP), 0.08)
rope2 = part("rope2", mb, flat((0.8, 0.7, 0.45)), tree_root)
hero = worker(tree_root, (ROPE_X + 11.3, -3, 0.12), (-1, 0.25), 1.2)
acts(hero, ("Idle_Loop", a, a + 30), ("Push_Loop", a + 30, snap - 2, True), ("Death01", snap - 2, snap + 40), ("Sitting_Idle_Loop", snap + 40, b))
vis(tree_root, (a, b))
vis(rope, (a, snap + 1))
vis(rope2, (a, snap + 1))
shot(a, b, (0, (11, -9, 2.2), (15.3, -3, 2.0)), (0.28, (10.5, -9.5, 2.5), (15, -3, 2.3)),
     (0.5, (0, -46, 6), (1, 0, 14)), (0.8, (3, -44, 6), (3, 0, 13)), (1, (6, -36, 4), (9, 0, 8)))

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
neon(A["jib"], W("jib", "beam") - 2, b2, 0.06)
set_hook(A, a3, 8, 18)
set_hook(A, a3 + 6, 8, 18)
set_hook(A, W("tip", "topple") + 4, 33, 18)
load = boxpart("Aload", (0, 0, -2.6), (3, 2.6, 2.2), (0.6, 0.6, 0.58), A["hook"])
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
for wt in A["weights"]:
    neon(wt, w_f, b4, 0.06)
neon(A["cj"], w_f, b4, 0.05)
neon(load, W("tip", "slide"), b3, 0.08)
vis(A["root"], (a2, b4))
# two of the crew talk it over while a third crosses the site
t1 = worker(loc=(-6, -20, 0.12), face=(1, 0.2))
t2 = worker(loc=(-3.6, -19.6, 0.12), face=(-1, -0.2))
for t_ in (t1, t2):
    acts(t_, ("Idle_Talking_Loop", a2, b2))
    vis(t_["root"], (a2, b2))
t3 = worker(face=(1, 0))
acts(t3, ("Walk_Loop", a2, b2))
stroll(t3, a2, b2, (-14, -14, 0.12), (10, -14, 0.12))
vis(t3["root"], (a2, b2))
# the same worker bolts as the crane leans, then dances once it is saved
run0 = W("tip", "whole") - 2
runner = worker(loc=(22, -16, 0.12), face=(-1, -0.25))
acts(runner, ("Idle_Loop", a3, run0), ("Sprint_Loop", run0, a4 + 8), ("Idle_Loop", a4 + 8, w_f + 28), ("Dance_Loop", w_f + 28, b4))
key(runner["root"], "location", run0, (22, -16, 0.12))
key(runner["root"], "location", a4 + 10, (-6, -24, 0.12))
vis(runner["root"], (a3, b4))
shot(a2, b2, (0, (-24, -50, 26), (2, 0, 18)), (1, (-16, -66, 44), (12, 0, 30)))
shot(a3, run0 - 1, (0, (-12, -68, 44), (14, 0, 30)), (1, (-6, -72, 42), (16, 0, 26)))
shot(run0, b3, (0, (15, -30, 1.9), (20, -17, 5)), (1, (-7, -33.5, 1.8), (2, -22, 7)))
shot(a4, w_f + 26, (0, (-38, -40, 46), (-6, 0, 30)), (1, (-30, -52, 46), (2, 0, 30)))
shot(w_f + 27, b4, (0, (-9.5, -33.5, 1.7), (-5.5, -24, 5)), (1, (-8, -33, 2.0), (-5.5, -24, 6)))

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
mb.box((0, 0, -7), (7, 5, 0.3))
for k in range(-1, 2, 2):
    mb.beam((k * 1.0, -1.25, -7), (k * 1.0, -1.25, -1.5), 0.32)  # hydraulic rams
cage = part("Ccage", mb, flat(BLACK), C["top"])
new_sec = obj("Cnew", section_mesh(ORANGE), (), C["root"], (14, 0, top0))
key(new_sec, "location", jack + 45, (14, 0, top0))
key(new_sec, "location", W("climb", "slides") + 18, (0, 0, top0))
fixer = worker(C["top"], (-2.8, -0.2, -7.0), (1, 0))
acts(fixer, ("Fixing_Kneeling", a, b))
spotter = worker(bld, (-6.5, -6.5, 35.3), (-1, 0.3))
acts(spotter, ("Idle_Talking_Loop", a, b))
neon(cage, jack - 2, b, 0.07)
neon(new_sec, W("climb", "fresh") - 2, b, 0.05)
vis(C["root"], (a, b))
vis(bld, (a, b))
shot(a, jack - 1, (0, (-30, -78, 22), (6, 0, 20)), (1, (-34, -78, 40), (6, 0, 30)))
shot(jack, b, (0, (-11, -19, 38), (1, 0, 36)), (1, (-13, -20, 40), (2, 0, 38)))

# ================================================================ 6. WIND
a, b = B("wind")
D = make_crane("D", 14, chain=True)
mb = MB()
mb.box((20, 4, 37), (20, 20, 74), (0.72, 0.72, 0.75), tile=3.6)
for sx in (-1, 1):
    mb.box((20 + sx * 10, 4, 74.6), (0.4, 20.4, 1.2), (0.3, 0.3, 0.32), wall=1)
    mb.box((20, 4 + sx * 10, 74.6), (20.4, 0.4, 1.2), (0.3, 0.3, 0.32), wall=1)
mb.box((24, 8, 75.5), (4, 5, 3), (0.5, 0.5, 0.52), wall=1)
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
for s in D["secs"]:
    neon(s, gust - 8, b, 0.05)
brace_w = worker(loc=(13, -3, 74), face=(-1, -0.4))
acts(brace_w, ("Idle_Loop", a, gust), ("Crouch_Idle_Loop", gust, b))
vis(D["root"], (a, b))
vis(block, (a, b))
vis(brace_w["root"], (a, b))
cw = gust + 30
shot(a, cw - 1, (0, (-20, -128, 62), (6, 0, 56)), (1, (-34, -122, 72), (8, 0, 64)))
shot(cw, b, (0, (17, -9, 77.8), (12.5, -2.5, 75.8)), (1, (18, -9, 77.6), (11, -1, 77)))

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
coll = part("Ecollar", mb, flat(BLACK), E["root"])
neon(coll, W("shaft", "braces") - 4, b, 0.09)
neon(E["secs"][0], W("shaft", "shaft") - 2, W("shaft", "every"), 0.05)
neon(E["secs"][1], W("shaft", "shaft") - 2, W("shaft", "every"), 0.05)
set_hook(E, a, 15, 10)
vis(E["root"], (a, b))
vis(bld2, (a, b))
for fz, kind, xy, fc_ in [(6, "Fixing_Kneeling", (-5.5, -7), (1, 0)), (7, "Idle_Talking_Loop", (4, -7.5), (-1, 0)),
                          (8, "Idle_Talking_Loop", (6.5, -7.5), (-1, 0.2))]:
    w_ = worker(bld2, (xy[0], xy[1], fz * fh + 0.18), fc_)
    acts(w_, (kind, a, b))
pusher = worker(bld2, face=(1, 0))
acts(pusher, ("Push_Loop", a, b))
stroll(pusher, a, b, (-8, -8, 4 * fh + 0.18), (7, -8, 4 * fh + 0.18))
shot(a, b, (0, (30, -46, 36), (0, 0, 32)), (0.5, (36, -46, 48), (0, 0, 42)), (1, (34, -50, 62), (0, 0, 54)))

# ================================================================ 8-10. ROOF
a8, b8 = B("stuck")
a9, b9 = B("derrick")
a10, b10 = B("smaller")
a11, b11 = B("end")
H = 150.0
mb = MB()
mb.box((0, 0, H / 2), (24, 24, H), (0.5, 0.6, 0.7), tile=3.4, wall=2)
mb.box((0, 0, 4), (26, 26, 8), (0.03, 0.03, 0.04), wall=1)              # lobby
for lv in range(1, 15):
    mb.box((0, 0, lv * 10), (24.25, 24.25, 0.3), (0.03, 0.03, 0.035), wall=1)
mb.box((0, 0, H + 0.6), (24, 24, 1.2), (0.22, 0.22, 0.24), wall=1)
for sx in (-1, 1):                                                       # parapet
    mb.box((sx * 11.8, 0, H + 1.6), (0.4, 24, 1.0), (0.05, 0.05, 0.06), wall=1)
    mb.box((0, sx * 11.8, H + 1.6), (24, 0.4, 1.0), (0.05, 0.05, 0.06), wall=1)
    mb.box((sx * 11.8, 0, H + 2.1), (0.45, 24, 0.12), ORANGE, wall=1)
    mb.box((0, sx * 11.8, H + 2.1), (24, 0.45, 0.12), ORANGE, wall=1)
for cx, cy, sx_, sy_ in [(-8, -8, 3, 2.4), (7.5, 8, 3.2, 3.2), (-1, 8.5, 2, 1.6)]:   # rooftop plant
    mb.box((cx, cy, H + 2.1), (sx_, sy_, 1.8), (0.42, 0.42, 0.44), wall=1)
    mb.box((cx, cy, H + 3.05), (sx_ * 0.6, sy_ * 0.6, 0.15), (0.1, 0.1, 0.11), wall=1)
for k in range(-4, 5):                                                    # gravel strips and vents
    mb.box((k * 2.6, -9.5, H + 1.24), (1.6, 0.8, 0.08), (0.3, 0.3, 0.31), wall=1)
tower = obj("skyscraper", mb.mesh("skyscraper"), [wall_mat, roof_mat, curtain_mat])
G = make_crane("G", 5, s=1, jib=30, loc=(0, 0, H))
set_hook(G, a8, 12, 10)
vis(tower, (a8, LAST))
vis(G["root"], (a8, b9))
ground = make_crane("Gr", 5, col_=BLACK, jib=24, cj=8, loc=(46, -28, 0))
vis(ground["root"], (a8, b8))
boss = worker(loc=(-3, -7, H + 1.2), face=(-0.45, -1))
acts(boss, ("Idle_Loop", a8, a8 + 40), ("Idle_Talking_Loop", a8 + 40, b9))
vis(boss["root"], (a8, b9))
neon(G["head"], W("stuck", "crane") - 2, b8, 0.05)
for s in G["secs"]:
    neon(s, W("stuck", "crane") - 2, b8, 0.05)
shot(a8, a8 + 70, (0, (-6.5, -11.2, H + 2.7), (-3, -7, H + 2.7)), (0.65, (-6.8, -11.3, H + 2.6), (-3, -7, H + 2.8)), (1, (-7.5, -11.4, H + 2.4), (-2, -6, H + 8)))
shot(a8 + 71, b8, (0, (22, -44, H + 34), (4, 0, H + 26)), (0.3, (26, -60, H + 26), (4, 0, H + 18)),
     (1, (46, -330, 92), (6, 0, 78)))

# the derrick arrives piece by piece on the big crane's hook
ROOF = H + 1.2
DX = 8
der = empty("derrick", loc=(DX, 0, ROOF))
mb = MB()
mb.box((0, 0, 0.4), (3, 3, 0.8))
d_base = part("d_base", mb, flat(BLACK), der)
mb = MB()
for x, y in [(-0.4, -0.4), (0.4, -0.4), (0.4, 0.4), (-0.4, 0.4)]:
    mb.beam((x, y, 0.8), (x, y, 11), 0.2)
for z in range(1, 11, 2):
    mb.beam((-0.4, -0.4, z), (0.4, 0.4, z + 1), 0.07)
d_mast = part("d_mast", mb, flat(BLACK), der)
mb = MB()
for y in (-0.3, 0.3):
    mb.beam((0, y, 11), (11, y, 21), 0.22)
for k in range(1, 8):
    x = k * 11 / 8
    mb.beam((x, -0.3, 11 + x * 10 / 11), (x + 1, 0.3, 11 + (x + 1) * 10 / 11), 0.06)
d_boom = part("d_boom", mb, flat(BLACK), der)
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
    # a sling cable runs up out of frame while the part is moving
    mbc = MB()
    mbc.beam((0, 0, 0), (0, 0, 1), 0.08, DARK)
    c_ = tpart(o.name + "_sling", mbc, o)
    key(c_, "scale", t0 - 1, (1, 1, 0))
    key(c_, "scale", t0, (1, 1, 45))
    key(c_, "scale", t0 + dur * 0.3, (1, 1, 43))
    key(c_, "scale", t0 + dur, (1, 1, 45 + drop))


t0 = W("derrick", "dismantles")
dur = 24
step_ = (b9 - t0 - dur) / 6
lower(G["jib"], t0, dur, (0, 0, 0), 14)
lower(G["cj"], t0 + step_, dur, (0, 0, 0), 26)
lower(G["head"], t0 + step_ * 2, dur, (0, 0, 0), 18)
for i, s in enumerate(reversed(G["secs"])):
    lower(s, t0 + step_ * (3 + i * 0.6), dur, (0, 0, (4 - i) * 6), 18)
for p_ in dlist:
    neon(p_, hook_f + 4, b10, 0.06)
mechanic = worker(der, (-2.2, -2.2, 0), (0.7, 0.7))
acts(mechanic, ("Fixing_Kneeling", a9, b10))
shot(a9, b9, (0, (24, -34, ROOF + 15), (5, 0, ROOF + 10)), (1, (30, -42, ROOF + 15), (8, 0, ROOF + 7)))

# the derrick is stranded; a smaller crane deals with it, then a smaller one still
M = make_crane("M", 2, col_=WHITE, s=0.45, jib=16, cj=6, loc=(-4, -6, ROOF))
tiny = make_crane("Tiny", 1, col_=ORANGE, s=0.22, jib=9, cj=3, loc=(-5, -8, ROOF))
tiny["top"].rotation_euler = (0, 0, math.pi / 2)
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
part("l_glow", mb, glow((1.0, 0.7, 0.42), 0.55), lift)
mb = MB()
mb.box((0, -0.12, 4.42), (W_ + 0.3, 0.2, 0.34), BLACK)                 # head with indicator strip
mb.box((0, -0.24, 4.42), (W_ * 0.5, 0.03, 0.12), ORANGE)
for sx in (-1, 1):
    mb.box((sx * (W_ / 2 + 0.05), -0.12, 2.2), (0.3, 0.2, 4.4), BLACK)
for k in range(10):                                                    # hazard threshold
    mb.box((-W_ / 2 + 0.2 + k * 0.4, -0.5, 0.03), (0.4, 0.5, 0.05), ORANGE if k % 2 else BLACK)
mb.box((W_ / 2 + 0.55, -0.1, 1.6), (0.32, 0.1, 0.6), (0.1, 0.1, 0.12))  # call panel
mb.box((W_ / 2 + 0.55, -0.16, 1.7), (0.12, 0.03, 0.12), ORANGE)
mb.box((W_ / 2 + 0.55, -0.16, 1.5), (0.12, 0.03, 0.12), (0.6, 0.6, 0.6))
for k in range(5):                                                     # cladding ribs on the shaft
    for sx in (-1, 1):
        mb.box((sx * (W_ / 2 + 0.11), 0.4 + k * 0.6, 2.25), (0.05, 0.14, 4.4), (0.45, 0.45, 0.45))
tpart("l_trim", mb, lift)
d1 = boxpart("door1", (0, 0, 2.2), (W_ / 2, 0.12, 4.2), (0.42, 0.44, 0.47), lift, (-W_ / 2 - 0.9, -0.05, 0))
d2 = boxpart("door2", (0, 0, 2.2), (W_ / 2, 0.12, 4.2), (0.42, 0.44, 0.47), lift, (W_ / 2 + 0.9, -0.05, 0))
walk = W("smaller", "last")
shut = walk + 36
key(tiny["root"], "location", walk, (-5, -8, ROOF))
key(tiny["root"], "location", shut - 2, (-5, 3.9, ROOF))
for d_, sg in ((d1, -1), (d2, 1)):
    key(d_, "location", shut - 1, (sg * (W_ / 2 + 0.9), -0.05, 0))
    key(d_, "location", shut + 12, (sg * W_ / 4, -0.05, 0))
vis(lift, (a8, LAST))
shot(a10, walk - 1, (0, (24, -40, ROOF + 12), (0, -2, ROOF + 5)), (1, (20, -38, ROOF + 10), (-2, -2, ROOF + 4)))
neon(tiny["head"], s2 + 2, b10, 0.08)
neon(tiny["jib"], s2 + 2, b10, 0.1)
for s in tiny["secs"]:
    neon(s, s2 + 2, b10, 0.1)
puller = worker(loc=(-5, -9.6, ROOF), face=(0, 1), scale=1.1)
acts(puller, ("Idle_Loop", s2, walk), ("Push_Loop", walk, shut - 2), ("Interact", shut - 2, shut + 24), ("Idle_Talking_Loop", shut + 24, b10))
key(puller["root"], "location", walk, (-5, -9.6, ROOF))
key(puller["root"], "location", shut - 2, (-5, 0.9, ROOF))
key(puller["root"], "location", shut + 6, (-3.4, 1.2, ROOF))
key(puller["root"], "rotation_euler", shut - 2, (0, 0, math.pi))
key(puller["root"], "rotation_euler", shut + 6, (0, 0, math.pi * 0.85))
vis(puller["root"], (s2, b10))
shot(walk, b10, (0, (-1.2, -14, ROOF + 2.2), (-4.8, -3, ROOF + 1.4)), (1, (-2.5, -7, ROOF + 2.0), (-4.8, 2.5, ROOF + 1.8)))

# ================================================================ 11. END
X = make_crane("X", 8, jib=34, loc=(-40, -22, 0))
set_hook(X, a11, 18, 14)
pop(X["cab"], W("end", "cab"), 8)
pop(X["hook"], W("end", "hook"), 8)
neon(X["cab"], W("end", "cab"), W("end", "someone"), 0.06)
neon(X["hook"], W("end", "hook"), W("end", "someone"), 0.1)
climber = worker(X["root"], (0, -1.25, 0), (0, 1), 1.0)
cl0 = W("end", "someone")
acts(climber, ("Walk_Loop", a11, LAST))
key(climber["root"], "location", cl0, (0, -1.25, 26))
key(climber["root"], "location", W("end", "congrat") - 2, (0, -1.25, 42))
for i, (dx, dy) in enumerate([(-2.8, 0), (0, 1.2), (2.8, 0), (-5.4, 1), (5.4, 1)]):
    d_ = worker(loc=(-37 + dx, -30.5 + dy, 0.12), face=(0.1 * -dx, -1))
    acts(d_, ("Idle_Loop", a11, W("end", "congrat") + 3 * i), ("Dance_Loop", W("end", "congrat") + 3 * i, LAST))
    vis(d_["root"], (a11, LAST))
vis(X["root"], (a11, LAST))
con = W("end", "congrat")
shot(a11, con - 1, (0, (-16, -40, 40), (-40, -22, 44)), (1, (-18, -42, 48), (-40, -22, 48)))
shot(con, LAST, (0, (-35, -41, 3.4), (-37, -28, 3.6)), (0.3, (-35, -42, 4), (-38, -22, 14)), (0.52, (-28, -58, 28), (-30, -10, 40)), (1, (6, -170, 44), (-16, 0, 66)))

# dawn for the driver's climb
# the world dims a little under each neon highlight so the glow carries
spans = sorted(HILITES)
merged = []
for a_, b_ in spans:
    if merged and a_ <= merged[-1][1] + 18:
        merged[-1][1] = max(merged[-1][1], b_)
    else:
        merged.append([a_, b_])
dim_v.outputs[0].default_value = 1.0
dim_v.outputs[0].keyframe_insert("default_value", frame=1)
key(sun_d, "energy", 1, 2.1)
for a_, b_ in merged:
    for f_, v_ in [(a_ - 1, 1.0), (a_ + 8, 0.74), (b_ - 3, 0.74), (b_ + 4, 1.0)]:
        dim_v.outputs[0].default_value = v_
        dim_v.outputs[0].keyframe_insert("default_value", frame=f_)
        key(sun_d, "energy", f_, 2.1 * v_)

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
scene.eevee.use_raytracing = True
scene.eevee.ray_tracing_options.resolution_scale = "2"
scene.eevee.fast_gi_method = "GLOBAL_ILLUMINATION"
scene.eevee.fast_gi_distance = 12
scene.use_nodes = True
cn = scene.node_tree
rl = cn.nodes["Render Layers"]
gl = cn.nodes.new("CompositorNodeGlare")
gl.glare_type = "FOG_GLOW"
gl.quality = "MEDIUM"
gl.size = 7
gl.threshold = 1.0
gl.mix = 0.0
cn.links.new(rl.outputs["Image"], gl.inputs["Image"])
cn.links.new(gl.outputs["Image"], cn.nodes["Composite"].inputs["Image"])
scene.render.resolution_x = 1080
scene.render.resolution_y = 1920
scene.render.fps = FPS
scene.frame_start = 1
scene.frame_end = LAST
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "None"
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 95
scene.render.filepath = os.path.join(HERE, "frames_v2", "f")
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
