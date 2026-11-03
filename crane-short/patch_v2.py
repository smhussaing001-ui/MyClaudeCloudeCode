"""One-shot upgrade of build_scene.py to v2. Fails loudly if an anchor is missing."""
import re

P = r"D:\Claude\crane-short\build_scene.py"
s = open(P, encoding="utf-8").read()


def sub(a, b, count=1):
    global s
    assert a in s, "MISSING: " + a[:70]
    s = s.replace(a, b) if count == 0 else s.replace(a, b, count)


def between(start, end, new):
    """Replace everything from `start` up to (not including) `end`."""
    global s
    i = s.index(start)
    j = s.index(end, i)
    s = s[:i] + new + s[j:]


s = re.sub(r"\bYELLOW\b", "ORANGE", s)
s = re.sub(r"\bRED\b", "BLACK", s)
sub("ORANGE = (0.95, 0.68, 0.05)", "ORANGE = (0.95, 0.23, 0.012)")
sub("BLACK = (0.75, 0.08, 0.10)", "BLACK = (0.014, 0.014, 0.017)\nNEON = (1.0, 0.28, 0.02)")
sub('col_=(0.15, 0.45, 0.8), s=0.45', "col_=WHITE, s=0.45")

# ---------------------------------------------------------------- facades
between("# a one-window facade tile", "roof_mat = bpy.data.materials.new", '''# facade tiles of 4x4 windows; alpha 1 = wall (takes the building tint), alpha 0 = glass
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
                a[y:y + cell, x:x + cell, :3] = np.array((0.06, 0.13, 0.22)) * g
                a[y:y + cell, x:x + cell, 3] = 0
                a[y:y + cell // 6, x:x + cell, :3] = (0.015, 0.018, 0.024)
                a[y:y + cell, x:x + 5, :3] = (0.015, 0.018, 0.024)
                continue
            r = rng.random()
            c = (0.95, 0.68, 0.34) if r < 0.09 else (0.05, 0.08, 0.13) if r < 0.6 else (0.1, 0.17, 0.27)
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
curtain_mat = building_mat("curtain", facade_image("curtain", True), False, 0.07, 0.07, 0.75)


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


''')

# ---------------------------------------------------------------- mesh builder
sub('''        self.v, self.f, self.uv, self.col, self.mi = [], [], [], [], []
''', '''        self.v, self.f, self.uv, self.col, self.mi = [], [], [], [], []
        self.cur = (1, 1, 1)
''')
sub('''    def add(self, verts, faces, col=(1, 1, 1), mat=0, uvs=None):
        s = len(self.v)''', '''    def add(self, verts, faces, col=None, mat=0, uvs=None):
        col = col or self.cur
        s = len(self.v)''')
sub('''    def box(self, c, s, col=(1, 1, 1), tile=None):''', '''    def box(self, c, s, col=None, tile=None, wall=0):''')
sub('''                u = round((s[0] if i % 2 == 0 else s[1]) / tile) or 1
                v = round(s[2] / tile) or 1
                self.add(vs, [fc], col, 0, [[(0, 0), (u, 0), (u, v), (0, v)]])''', '''                u = (round((s[0] if i % 2 == 0 else s[1]) / tile) or 1) / 4
                v = (round(s[2] / tile) or 1) / 4
                self.add(vs, [fc], col, wall, [[(0, 0), (u, 0), (u, v), (0, v)]])''')
sub('''            self.add(vs, sides + cap, col)
''', '''            self.add(vs, sides + cap, col, wall)
''')
sub('''    def beam(self, p, q, t=0.12):''', '''    def beam(self, p, q, t=0.12, col=None):''')
sub('''(3, 2, 1, 0), (4, 5, 6, 7)])

    def mesh''', '''(3, 2, 1, 0), (4, 5, 6, 7)], col)

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

    def mesh''')


# ---------------------------------------------------------------- neon + helpers
sub('''# ---------------------------------------------------------------- animation helpers
''', '''def tpart(name, mb, parent=None, loc=(0, 0, 0)):
    """Multi-coloured part: colours come from the mesh's tint attribute."""
    return obj(name, mb.mesh(name), [roof_mat], parent, loc)


def smooth(o):
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    o.data.update()
    return o


# ---------------------------------------------------------------- animation helpers
''')
sub('''def apply_vis():
    def walk(o):
        yield o
        for c in o.children:
            yield from walk(c)

    for root, ranges in VIS:
        for o in walk(root):
''', '''NEONS, HILITES = [], []


def neon(o, a, b, thick=0.05, power=16.0):
    """Wrap an object in a pulsing neon-orange shell between frames a and b."""
    c = obj(o.name + "_neon", o.data, (), o)
    m = bpy.data.materials.new(o.name + "_neon")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out_ = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (*NEON, 1)
    nt.links.new(em.outputs[0], out_.inputs[0])
    for sl in c.material_slots:
        sl.link = "OBJECT"
        sl.material = m
    sol = c.modifiers.new("shell", "SOLIDIFY")
    sol.thickness = thick
    sol.offset = 1
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
''')

# ---------------------------------------------------------------- crane
between("def section_mesh(col_):", "def set_hook(c, f", '''def section_mesh(col_):
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


''')

# ---------------------------------------------------------------- floors
sub('''        floors.append(part(f"{name}_{i}", mb, flat(CONCRETE), root, (0, 0, (i + 1) * fh)))''',
    '''        mb.cur = CONCRETE
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
        floors.append(tpart(f"{name}_{i}", mb, root, (0, 0, (i + 1) * fh)))''')

# ---------------------------------------------------------------- city
sub('''mb.box((x, y, h / 2), (w, d, h), hue, tile=3.6)
        mb.box((x, y, h + 0.25), (w, d, 0.5), random.choice(ROOFS), tile=1000)''',
    '''tower_type = h > 70 and random.random() < 0.45
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
                mb.box((x, y, lv * 14), (w + 0.7, d + 0.7, 0.45), hue, wall=1)''')
sub('''    mb.box((x, y, h / 2), (w, d, h), hue, tile=3.2)
''', '''    mb.box((x, y, h / 2), (w, d, h), hue, tile=3.2)
    mb.box((x - 2, y - d / 2 - 0.06, 1.3), (1.6, 0.12, 2.6), (0.08, 0.06, 0.05), wall=1)   # door
    mb.box((x, y - d / 2 - 0.4, 2.9), (w, 0.8, 0.2), (0.9, 0.9, 0.88), wall=1)
    mb.box((x + 3.5, y + 2, h + 4), (1.2, 1.2, 3), (0.5, 0.3, 0.25), wall=1)               # chimney
''')
sub('''city = obj("city", mb.mesh("city"), [wall_mat, roof_mat])''', '''city = obj("city", mb.mesh("city"), [wall_mat, roof_mat, curtain_mat])''')
sub('''part("ground", mb, flat((0.42, 0.43, 0.47)))''', '''part("ground", mb, proc("asphalt0", (0.16, 0.16, 0.18), (0.27, 0.27, 0.29), 0.25, 0.9, 0.2))''')
sub('''part("road", mb, flat((0.25, 0.26, 0.29)))''', '''part("road", mb, proc("asphalt", (0.05, 0.05, 0.06), (0.1, 0.1, 0.11), 3, 0.85, 0.3))''')
sub('''part("site", mb, flat((0.36, 0.24, 0.15)))''', '''part("site", mb, proc("dirt", (0.13, 0.075, 0.04), (0.33, 0.21, 0.12), 0.9, 1.0, 1.0))''')
between("def tree(mb_t, mb_f, x, y, s):", "trunks, leaves = MB(), MB()", '''LEAF_MAT = proc("leaf", (0.03, 0.17, 0.03), (0.2, 0.48, 0.09), 2.2, 0.75, 1.5)


def ball(mb_f, c, r):
    mb_f.ball(c, r)


def tree(mb_t, mb_f, x, y, s):
    mb_t.box((x, y, 2 * s), (0.5 * s, 0.5 * s, 4 * s))
    for dx, dy, dz, r in [(0, 0, 5, 2.4), (1.5, 0.5, 4.2, 1.6), (-1.4, -0.6, 4.4, 1.7), (0.2, 1.2, 6, 1.5),
                          (-0.8, 1, 5.6, 1.4), (1, -1, 5.5, 1.3), (0, -1.4, 4.5, 1.3)]:
        ball(mb_f, (x + dx * s, y + dy * s, dz * s), r * s)


''')
sub('''tr_leaf = part("trees_f", leaves, flat(LEAF))''', '''tr_leaf = part("trees_f", leaves, LEAF_MAT)''')
sub('''crown = part("crown", mb, flat(LEAF), tree_root)''', '''crown = part("crown", mb, LEAF_MAT, tree_root)''')
sub('''tuft = part("tuft", mb, flat(LEAF), branch)''', '''tuft = part("tuft", mb, LEAF_MAT, branch)''')
sub('''for dx, dy, dz, r in [(0, 0, 20, 8), (-6, 3, 16, 6), (-3, -5, 15, 5.5), (4, 4, 17, 6)]:''',
    '''for dx, dy, dz, r in [(0, 0, 20, 8), (-6, 3, 16, 6), (-3, -5, 15, 5.5), (4, 4, 17, 6), (-5, -3, 23, 5), (3, -4, 22, 5), (-9, 0, 20, 5), (5, 2, 24, 4.5)]:''')
sub('''mb.beam((TX, 0, 0), (TX, 0, 15), 2.0)
part("trunk", mb, flat(TRUNK), tree_root)''', '''mb.beam((TX, 0, 0), (TX, 0, 15), 2.0)
trunk_mat = proc("bark", (0.05, 0.03, 0.015), (0.2, 0.12, 0.07), 6, 1.0, 1.5)
part("trunk", mb, trunk_mat, tree_root)''')
sub('''part("limb", mb, flat(TRUNK), branch)''', '''part("limb", mb, trunk_mat, branch)''')

# ---------------------------------------------------------------- lighting + crew + props block
sub('''# ================================================================ 1. BRANCH
''', r'''# ---------------------------------------------------------------- street and site dressing
mb = MB()
mb.box((0, -42.1, 0.12), (420, 2.2, 0.24), (0.42, 0.42, 0.4))      # kerbs and pavements
mb.box((0, -62, 0.12), (420, 2.2, 0.24), (0.42, 0.42, 0.4))
for i in range(-22, 23):
    mb.box((i * 9, -52, 0.09), (4.5, 0.25, 0.02), (0.85, 0.85, 0.8))
    if i % 4 == 0:                                                 # street lamps
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
for x in range(-42, 43, 4):                                         # front is open mesh fencing
    mb.beam((x, -35, 0), (x, -35, 2.1), 0.07, (0.3, 0.3, 0.32))
    mb.beam((x, -35, 2.1), (min(x + 4, 42), -35, 2.1), 0.05, (0.3, 0.3, 0.32))
    mb.beam((x, -35, 1.0), (min(x + 4, 42), -35, 1.0), 0.03, (0.3, 0.3, 0.32))
    mb.box((x, -35, 0.08), (0.5, 0.5, 0.16), ORANGE)

# crane base pad with hazard edge
mb.box((0, 0, 0.3), (9, 9, 0.6), CONCRETE)
for k in range(9):
    q = -4.5 + k + 0.5
    c = ORANGE if k % 2 else BLACK
    mb.box((q, -4.52, 0.3), (1, 0.05, 0.6), c)
    mb.box((-4.52, q, 0.3), (0.05, 1, 0.6), c)

# site cabins
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
dressing = tpart("dressing", mb)
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
me_.materials.clear()
for m_ in [flat(ORANGE, 0.55), flat((0.025, 0.027, 0.035), 0.8), flat((0.62, 0.36, 0.24), 0.5),
           flat((0.012, 0.012, 0.012), 0.6), glow((1.0, 0.92, 0.65), 1.2)]:
    me_.materials.append(m_)
for p_ in me_.polygons:
    g = max(set(dom[i] for i in p_.vertices), key=[dom[i] for i in p_.vertices].count)
    cz = p_.center.z / HT
    if "head" in g or "neck" in g:
        mi = 2
    elif "hand" in g or "f_" in g or "thumb" in g or "foot" in g or "toe" in g:
        mi = 3
    elif "spine" in g or "shoulder" in g:
        mi = 4 if 0.60 < cz < 0.625 or 0.70 < cz < 0.72 else 0
    else:
        mi = 1
    p_.material_index = mi
HEAD_BONE = BASE_ARM.data.bones["DEF-head"]
HEAD_INV = (HEAD_BONE.matrix_local @ Matrix.Translation((0, HEAD_BONE.length, 0))).inverted()

mb = MB()
SKIN = (0.62, 0.36, 0.24)
mb.ball((HEAD_CX, HEAD_Y + 0.13, HEAD_TOP - 0.035), 0.125, ORANGE, sz=0.82, rows=7, cols=14)  # hard hat
for k in range(18):
    a0, a1 = k * math.tau / 18, (k + 1) * math.tau / 18
    mb.beam((HEAD_CX + 0.135 * math.cos(a0), HEAD_Y + 0.11 + 0.15 * math.sin(a0), HEAD_TOP - 0.05),
            (HEAD_CX + 0.135 * math.cos(a1), HEAD_Y + 0.11 + 0.15 * math.sin(a1), HEAD_TOP - 0.05), 0.022, ORANGE)
mb.box((HEAD_CX, HEAD_Y + 0.02, HEAD_TOP - 0.02), (0.16, 0.05, 0.03), BLACK)
mb.ball((HEAD_CX, HEAD_Y - 0.008, HEAD_MIDZ - 0.012), 0.016, SKIN, sz=1.1, rows=4, cols=6)      # nose
mb.beam((HEAD_CX - 0.028, HEAD_Y + 0.006, HEAD_MIDZ - 0.048), (HEAD_CX + 0.028, HEAD_Y + 0.006, HEAD_MIDZ - 0.045), 0.009, (0.16, 0.05, 0.04))
for sx in (-1, 1):
    mb.beam((HEAD_CX + sx * 0.022, HEAD_Y + 0.004, HEAD_MIDZ + 0.042), (HEAD_CX + sx * 0.06, HEAD_Y + 0.016, HEAD_MIDZ + 0.05), 0.013, (0.05, 0.03, 0.02))
FACE_ME = mb.mesh("face")
FACE_ME.materials.append(roof_mat)
FACE_ME.polygons.foreach_set("use_smooth", [True] * len(FACE_ME.polygons))
mb = MB()
for sx in (-1, 1):
    mb.ball((sx * 0.04, 0, 0), 0.021, (0.9, 0.9, 0.88), rows=5, cols=8)
    mb.ball((sx * 0.04, -0.012, 0), 0.012, (0.01, 0.01, 0.012), rows=4, cols=6)
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
    for data, l_ in ((FACE_ME, (0, 0, 0)), (EYES_ME, (HEAD_CX, HEAD_Y + 0.012, HEAD_MIDZ + 0.012))):
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
''')

sub('''person = empty("person", tree_root, (ROPE_X + 11.3, -3, 0))
boxpart("body", (0, 0, 1.6), (0.6, 0.4, 1.2), (0.85, 0.2, 0.1), person)
boxpart("legs", (0, 0, 0.5), (0.5, 0.35, 1.0), (0.1, 0.15, 0.3), person)
boxpart("head_p", (0, 0, 2.5), (0.42, 0.42, 0.42), (0.9, 0.7, 0.55), person)
''', '''hero = worker(tree_root, (ROPE_X + 11.3, -3, 0.12), (-1, 0.25), 1.2)
acts(hero, ("Idle_Loop", a, a + 30), ("Push_Loop", a + 30, snap - 2, True), ("Death01", snap - 2, snap + 40), ("Sitting_Idle_Loop", snap + 40, b))
''')
sub('''shot(a, b, (0, (-2, -50, 6), (1, 0, 15)), (0.6, (2, -47, 6), (2, 0, 14)), (1, (4, -45, 5), (3, 0, 12)))''',
    '''shot(a, b, (0, (8.5, -11.5, 2.6), (15.3, -3, 2.2)), (0.28, (8, -12.5, 3), (14.5, -3, 2.6)),
     (0.5, (0, -46, 6), (1, 0, 14)), (0.8, (3, -44, 6), (3, 0, 13)), (1, (6, -36, 4), (9, 0, 8)))''')

# 2-4
sub('''set_hook(A, a3, 8, 18)''', '''neon(A["jib"], W("jib", "beam") - 2, b2, 0.06)
set_hook(A, a3, 8, 18)''')
sub('''load = boxpart("Aload", (0, 0, -1.5), (3, 2.6, 2.2)''', '''load = boxpart("Aload", (0, 0, -2.6), (3, 2.6, 2.2)''')
sub('''vis(A["root"], (a2, b4))
''', '''for wt in A["weights"]:
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
''')
sub('''shot(a3, b3, (0, (-12, -68, 44), (14, 0, 30)), (1, (-2, -74, 40), (18, 0, 24)))''',
    '''shot(a3, run0 - 1, (0, (-12, -68, 44), (14, 0, 30)), (1, (-6, -72, 42), (16, 0, 26)))
shot(run0, b3, (0, (6, -38, 2.2), (20, -14, 12)), (1, (-14, -42, 2.0), (2, -20, 10)))''')
sub('''shot(a4, b4, (0, (-38, -40, 46), (-6, 0, 34)), (1, (-28, -66, 48), (6, 0, 30)))''',
    '''shot(a4, w_f + 26, (0, (-38, -40, 46), (-6, 0, 30)), (1, (-30, -52, 46), (2, 0, 30)))
shot(w_f + 27, b4, (0, (-12, -35, 1.8), (-5.5, -24, 6)), (1, (-9, -33, 2.2), (-5, -24, 7)))''')

# 5
sub('''vis(C["root"], (a, b))
vis(bld, (a, b))''', '''fixer = worker(C["top"], (-2.8, -0.2, -7.0), (1, 0))
acts(fixer, ("Fixing_Kneeling", a, b))
spotter = worker(bld, (-6.5, -6.5, 35.3), (-1, 0.3))
acts(spotter, ("Idle_Talking_Loop", a, b))
neon(C["top"].children[-1], jack - 2, b, 0.07)
neon(new_sec, W("climb", "fresh") - 2, b, 0.05)
vis(C["root"], (a, b))
vis(bld, (a, b))''')
sub('''mb.box((0, 0, -7), (4, 4, 0.3))
part("Ccage", mb, flat(BLACK), C["top"])''', '''mb.box((0, 0, -7), (7, 5, 0.3))
for k in range(-1, 2, 2):
    mb.beam((k * 1.0, -1.25, -7), (k * 1.0, -1.25, -1.5), 0.32)  # hydraulic rams
part("Ccage", mb, flat(BLACK), C["top"])''')
sub('''shot(jack, b, (0, (-16, -26, 46), (2, 0, 40)), (1, (-20, -24, 42), (4, 0, 40)))''',
    '''shot(jack, b, (0, (-11, -19, 38), (1, 0, 36)), (1, (-13, -20, 40), (2, 0, 38)))''')

# 6
sub('''vis(D["root"], (a, b))
vis(block, (a, b))
shot(a, b, (0, (-20, -128, 62), (6, 0, 56)), (1, (-34, -122, 72), (8, 0, 64)))''', '''for s in D["secs"]:
    neon(s, gust - 8, b, 0.05)
brace_w = worker(loc=(13, -3, 74), face=(-1, -0.4))
acts(brace_w, ("Idle_Loop", a, gust), ("Crouch_Idle_Loop", gust, b))
vis(D["root"], (a, b))
vis(block, (a, b))
vis(brace_w["root"], (a, b))
cw = gust + 30
shot(a, cw - 1, (0, (-20, -128, 62), (6, 0, 56)), (1, (-34, -122, 72), (8, 0, 64)))
shot(cw, b, (0, (20, -18, 76.5), (8, -1, 80)), (1, (22, -16, 76), (6, 0, 82)))''')
sub('''mb.box((20, 4, 37), (20, 20, 74), (0.72, 0.72, 0.75), tile=3.6)
block = obj("block6", mb.mesh("block6"), [wall_mat, roof_mat])''', '''mb.box((20, 4, 37), (20, 20, 74), (0.72, 0.72, 0.75), tile=3.6)
for sx in (-1, 1):
    mb.box((20 + sx * 10, 4, 74.6), (0.4, 20.4, 1.2), (0.3, 0.3, 0.32), wall=1)
    mb.box((20, 4 + sx * 10, 74.6), (20.4, 0.4, 1.2), (0.3, 0.3, 0.32), wall=1)
mb.box((24, 8, 75.5), (4, 5, 3), (0.5, 0.5, 0.52), wall=1)
block = obj("block6", mb.mesh("block6"), [wall_mat, roof_mat])''')

# 7
sub('''part("Ecollar", mb, flat(BLACK), E["root"])
set_hook(E, a, 15, 10)
vis(E["root"], (a, b))
vis(bld2, (a, b))''', '''coll = part("Ecollar", mb, flat(BLACK), E["root"])
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
stroll(pusher, a, b, (-8, -8, 4 * fh + 0.18), (7, -8, 4 * fh + 0.18))''')

# 8-10 roof
between('''mb.box((0, 0, H / 2), (24, 24, H), (0.18, 0.28, 0.46), tile=3.4)''', '''G = make_crane("G", 5''', '''mb.box((0, 0, H / 2), (24, 24, H), (0.5, 0.6, 0.7), tile=3.4, wall=2)
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
''')
sub('''shot(a8, b8, (0, (22, -44, H + 34), (4, 0, H + 26)), (0.35, (26, -60, H + 26), (4, 0, H + 18)),
     (1, (46, -330, 92), (6, 0, 78)))''', '''boss = worker(loc=(-3, -7, H + 1.2), face=(0.5, 1))
acts(boss, ("Idle_Loop", a8, a8 + 40), ("Idle_Talking_Loop", a8 + 40, b9))
vis(boss["root"], (a8, b9))
neon(G["head"], W("stuck", "crane") - 2, b8, 0.05)
for s in G["secs"]:
    neon(s, W("stuck", "crane") - 2, b8, 0.05)
shot(a8, a8 + 70, (0, (-8, -17, H + 2.8), (-3, -7, H + 3.4)), (1, (-9, -18, H + 2.4), (-2, -6, H + 8)))
shot(a8 + 71, b8, (0, (22, -44, H + 34), (4, 0, H + 26)), (0.3, (26, -60, H + 26), (4, 0, H + 18)),
     (1, (46, -330, 92), (6, 0, 78)))''')
sub('''def lower(o, t0, dur, base, dx, up=1.5, drop=H + 30):
    """Sling a part sideways off the roof edge and lower it to the street."""
    bx, by, bz = base
    key(o, "location", t0, (bx, by, bz))
    key(o, "location", t0 + dur * 0.3, (bx + dx, by, bz + up))
    key(o, "location", t0 + dur, (bx + dx, by, bz - drop))''', '''def lower(o, t0, dur, base, dx, up=1.5, drop=H + 30):
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
    key(c_, "scale", t0 + dur, (1, 1, 45 + drop))''')
sub('''shot(a9, b9, (0, (30, -46, ROOF + 22), (4, 0, ROOF + 14)), (1, (34, -50, ROOF + 18), (8, 0, ROOF + 6)))''',
    '''for p_ in dlist:
    neon(p_, hook_f + 4, b10, 0.06)
mechanic = worker(der, (-2.2, -2.2, 0), (0.7, 0.7))
acts(mechanic, ("Fixing_Kneeling", a9, b10))
shot(a9, b9, (0, (24, -34, ROOF + 15), (5, 0, ROOF + 10)), (1, (30, -42, ROOF + 15), (8, 0, ROOF + 7)))''')
sub('''shot(walk, b10, (0, (-3, -21, ROOF + 4), (-5, 0, ROOF + 1.6)), (1, (-4, -18, ROOF + 3.4), (-5, 2, ROOF + 2)))''',
    '''neon(tiny["head"], s2 + 2, b10, 0.08)
neon(tiny["jib"], s2 + 2, b10, 0.1)
for s in tiny["secs"]:
    neon(s, s2 + 2, b10, 0.1)
puller = worker(loc=(-5, -9.6, ROOF), face=(0, 1), scale=1.1)
acts(puller, ("Idle_Loop", s2, walk), ("Push_Loop", walk, shut - 2), ("Interact", shut - 2, shut + 24), ("Idle_Talking_Loop", shut + 24, b10))
key(puller["root"], "location", walk, (-5, -9.6, ROOF))
key(puller["root"], "location", shut - 2, (-5, 1.6, ROOF))
key(puller["root"], "location", shut + 6, (-3.4, 1.2, ROOF))
key(puller["root"], "rotation_euler", shut - 2, (0, 0, math.pi))
key(puller["root"], "rotation_euler", shut + 6, (0, 0, math.pi * 0.85))
vis(puller["root"], (s2, b10))
shot(walk, b10, (0, (-1.2, -14, ROOF + 2.2), (-4.8, -3, ROOF + 1.4)), (1, (-2.5, -7, ROOF + 2.0), (-4.8, 2.5, ROOF + 1.8)))''')

# 11 end
sub('''climber = boxpart("climber", (0, 0, 1), (1.0, 0.7, 2), (0.9, 0.25, 0.08), X["root"], (0, -1.45, 0))
cl0 = W("end", "someone")
key(climber, "location", cl0, (0, -1.45, 26))
key(climber, "location", W("end", "congrat") - 2, (0, -1.45, 46))
''', '''neon(X["cab"], W("end", "cab"), W("end", "someone"), 0.06)
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
''')
sub('''shot(a11, con - 1, (0, (-14, -38, 44), (-38, -22, 46)), (1, (-16, -40, 50), (-38, -22, 48)))
shot(con, LAST, (0, (-34, -94, 34), (-30, -10, 46)), (1, (10, -210, 58), (-14, 0, 68)))''',
    '''shot(a11, con - 1, (0, (-16, -40, 40), (-40, -22, 44)), (1, (-18, -42, 48), (-40, -22, 48)))
shot(con, LAST, (0, (-34, -41, 2.4), (-37.5, -22, 7)), (0.3, (-34, -42, 3), (-38, -22, 18)), (1, (6, -170, 44), (-16, 0, 66)))''')
sub('''for f, sky, sn, hz in [(a11 - 1, (1, 1, 1, 1), (1, 1, 1), hz_color),''', '''# the world dims a little under each neon highlight so the glow carries
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
    for f_, v_ in [(a_ - 1, 1.0), (a_ + 8, 0.62), (b_ - 3, 0.62), (b_ + 4, 1.0)]:
        dim_v.outputs[0].default_value = v_
        dim_v.outputs[0].keyframe_insert("default_value", frame=f_)
        key(sun_d, "energy", f_, 2.1 * v_)

for f, sky, sn, hz in [(a11 - 1, (1, 1, 1, 1), (1, 1, 1), hz_color),''')
sub('''nt.links.new(bs_mix.outputs[0], bg.inputs[1])''', '''dim_v = nt.nodes.new("ShaderNodeValue")
dim_m = nt.nodes.new("ShaderNodeMath")
dim_m.operation = "MULTIPLY"
nt.links.new(bs_mix.outputs[0], dim_m.inputs[0])
nt.links.new(dim_v.outputs[0], dim_m.inputs[1])
nt.links.new(dim_m.outputs[0], bg.inputs[1])''')
sub('''sun_d.angle = math.radians(2)''', '''sun_d.angle = math.radians(1.2)''')
sub('''from mathutils import Vector''', '''from mathutils import Matrix, Vector''')

# render + bloom
sub('''scene.eevee.taa_render_samples = 16
''', '''scene.eevee.taa_render_samples = 24
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
gl.size = 8
gl.threshold = 1.15
gl.mix = 0.15
cn.links.new(rl.outputs["Image"], gl.inputs["Image"])
cn.links.new(gl.outputs["Image"], cn.nodes["Composite"].inputs["Image"])
''')
open(P, "w", encoding="utf-8").write(s)
print("patched")
