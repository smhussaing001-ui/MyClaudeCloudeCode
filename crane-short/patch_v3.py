"""Apply the v3 fixes to build_scene.py and finish.py. Every edit must match exactly once."""
s = open("build_scene.py", encoding="utf-8").read()


def R(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:70])
    s = s.replace(old, new)


def between(start, end, new):
    """Replace from `start` up to, not including, `end`."""
    global s
    assert s.count(start) == 1, start
    i = s.index(start)
    j = s.index(end, i)
    s = s[:i] + new + s[j:]


R('"frames_v2", "f"', '"frames_v3", "f"')

# 1. the camera ends close enough to see the worker fall when the branch goes
R("(1, (6, -36, 4), (9, 0, 8)))", "(1, (11, -24, 3.2), (9, 0, 7)))")

# 6. the fishing-rod line now shows the crane flexing behind the worker
R("shot(cw, b, (0, (17, -9, 77.8), (12.5, -2.5, 75.8)), (1, (18, -9, 77.6), (11, -1, 77)))",
  "shot(cw, b, (0, (20, -12, 75.6), (7, -1, 84)), (1, (21, -12, 75.4), (5, -1, 86)))")

# 7. neon on the whole mast for the whole beat, plus a close look at the jacking
between('neon(E["secs"][0], W("shaft", "shaft")', 'set_hook(E, a, 15, 10)',
        'for s_ in E["secs"]:\n    neon(s_, W("shaft", "shaft") - 2, b, 0.07)\n')
R("shot(a, b, (0, (30, -46, 36), (0, 0, 32)), (0.5, (36, -46, 48), (0, 0, 42)), (1, (34, -50, 62), (0, 0, 54)))",
  '''ev = W("shaft", "every")
con_ = W("shaft", "concrete")
fz_ = 9 * fh + 0.18
watcher = worker(bld2, (3.6, -5.2, fz_), (-0.7, 0.7))
acts(watcher, ("Idle_Talking_Loop", a, b))
shot(a, ev - 1, (0, (30, -46, 36), (0, 0, 32)), (1, (36, -46, 48), (0, 0, 42)))
shot(ev, con_ - 1, (0, (8.2, -9.4, fz_ + 1.6), (0.5, 0, fz_ + 1.5)), (1, (7.4, -9.4, fz_ + 1.7), (0.5, 0, fz_ + 1.6)))
shot(con_, b, (0, (36, -48, 56), (0, 0, 48)), (1, (34, -50, 62), (0, 0, 54)))''')

# 8. the ground crane glows on the line that says it cannot reach
R('''neon(G["head"], W("stuck", "crane") - 2, b8, 0.05)''',
  '''nw = W("stuck", "nothing") - 2
for p_ in ground["secs"] + [ground["jib"], ground["head"]]:
    neon(p_, nw, b8, 0.22)
neon(G["head"], W("stuck", "crane") - 2, b8, 0.05)''')

# 9. a taller derrick, set beside the big crane, that really carries each part on a cable
R('der = empty("derrick", loc=(DX, 0, ROOF))', 'der = empty("derrick", loc=(DX, -5, ROOF))')
between("for y in (-0.3, 0.3):\n    mb.beam((0, y, 11), (11, y, 21), 0.22)", 'd_boom = part("d_boom"',
        '''for y in (-0.3, 0.3):
    mb.beam((0, y, 11), (11, 5 + y, 15), 0.22)
for k in range(1, 8):
    q = k / 8
    mb.beam((11 * q, 5 * q - 0.3, 11 + 4 * q), (11 * (q + 0.1), 5 * (q + 0.1) + 0.3, 11 + 4 * (q + 0.1)), 0.06)
''')
between("hook_f = a9 + 4\n", "def lower(o, t0, dur", '''hook_f = a9 + 4
dlist = [d_base, d_mast, d_boom]
TROLLEY_Z = 29.6  # the big crane's trolley above the roof
key(G["top"], "rotation_euler", a9 - 1, (0, 0, 0))
ang_ = math.atan2(-5, DX)
for i, (p_, ptop, off, r_, an_) in enumerate([(d_base, 0.8, 22, math.hypot(DX, 5), ang_),
                                              (d_mast, 11, 11, math.hypot(DX, 5), ang_),
                                              (d_boom, 15, 8, math.hypot(13.5, 2.5), math.atan2(-2.5, 13.5))]):
    t0 = hook_f + 4 + i * 22
    key(G["top"], "rotation_euler", t0 - 3, (0, 0, an_))
    set_hook(G, t0 - 3, r_, None)
    key(p_, "location", t0 - 1, (0, 0, off))
    key(p_, "location", t0 + 18, (0, 0, 0))
    set_hook(G, t0 - 1, None, TROLLEY_Z - (ptop + off + 0.7))
    set_hook(G, t0 + 18, None, TROLLEY_Z - (ptop + 0.7))
    set_hook(G, t0 + 21, None, 7)
    pop(p_, t0 - 3, 2)
tele0, tele1 = hook_f + 4 + 44 + 18, W("derrick", "dismantles") - 2
print("TELE", tele0, tele1)
key(G["top"], "rotation_euler", tele0, (0, 0, math.atan2(-2.5, 13.5)))
key(G["top"], "rotation_euler", tele1, (0, 0, 0))
key(d_mast, "scale", tele0, (1, 1, 1))
key(d_mast, "scale", tele1, (1, 1, 34 / 11))
key(d_boom, "location", tele0, (0, 0, 0))
key(d_boom, "location", tele1, (0, 0, 23))
TIP_D = empty("tipD", d_boom, (11, 5, 15))


''')
between("def lower(o, t0, dur", 't0 = W("derrick", "dismantles")', '''def lower(o, t0, dur, base, dx, tip, attach=(0, 0, 0), up=1.5, drop=H + 30):
    """Lift a part off with a real cable from `tip`, swing it clear of the roof, lower it to the street."""
    bx, by, bz = base
    key(o, "location", t0, (bx, by, bz))
    key(o, "location", t0 + dur * 0.3, (bx + dx, by, bz + up))
    key(o, "location", t0 + dur, (bx + dx, by, bz - drop))
    tg = empty(o.name + "_pick", o, attach)
    mbc = MB()
    mbc.box((0, 0, 0), (0.7, 0.45, 0.8), ORANGE)
    pop(tpart(o.name + "_block", mbc, tg), t0 - 1, 1)
    mbc = MB()
    mbc.beam((0, 0, 0), (0, 0, 1), 0.1, DARK)
    c_ = tpart(o.name + "_sling", mbc)
    cl_ = c_.constraints.new("COPY_LOCATION")
    cl_.target = tip
    st_ = c_.constraints.new("STRETCH_TO")
    st_.target = tg
    st_.rest_length = 1.0
    st_.volume = "NO_VOLUME"
    st_.keep_axis = "PLANE_X"
    for f_, h_ in [(1, True), (t0, False), (t0 + dur + 1, True)]:
        c_.hide_render = h_
        c_.keyframe_insert("hide_render", frame=int(f_))


''')
between('lower(G["jib"], t0, dur, (0, 0, 0), 14)', "for p_ in dlist:\n    neon(p_",
        '''lower(G["jib"], t0, dur, (0, 0, 0), 14, TIP_D, (6, 0, 2.5))
lower(G["cj"], t0 + step_, dur, (0, 0, 0), 26, TIP_D, (-7, 0, 2))
lower(G["head"], t0 + step_ * 2, dur, (0, 0, 0), 23, TIP_D, (0, 0, 1))
for i, s in enumerate(reversed(G["secs"])):
    lower(s, t0 + step_ * (3 + i * 0.6), dur, (0, 0, (4 - i) * 6), 18, TIP_D, (0, 0, 6))
''')
R("shot(a9, b9, (0, (24, -34, ROOF + 15), (5, 0, ROOF + 10)), (1, (30, -42, ROOF + 15), (8, 0, ROOF + 7)))",
  "shot(a9, b9, (0, (40, -74, ROOF + 26), (9, 0, ROOF + 18)), (1, (46, -80, ROOF + 26), (11, 0, ROOF + 16)))")

# 10. each smaller crane folds the last one down, then lifts it away on its own cable
between('M = make_crane("M", 2,', "vis(der, (a9, b10))", '''M = make_crane("M", 4, col_=WHITE, s=0.7, jib=24, cj=8, loc=(0, -8, ROOF))
tiny = make_crane("Tiny", 1, col_=ORANGE, s=0.45, jib=9, cj=3, loc=(9, -8, ROOF))
TIP_M = empty("tipM", M["jib"], (25, 0, 1.5))
TIP_T = empty("tipT", tiny["jib"], (10, 0, 1.5))
s0 = W("smaller", "so")
pop(M["root"], s0, 8, (0.7,) * 3)
s1 = s0 + 22
key(d_mast, "scale", s0 + 6, (1, 1, 34 / 11))
key(d_mast, "scale", s1 - 2, (1, 1, 1))
key(d_boom, "location", s0 + 6, (0, 0, 23))
key(d_boom, "location", s1 - 2, (0, 0, 0))
lower(d_boom, s1, 18, (0, 0, 0), 6, TIP_M, (5, 2, 13))
lower(d_mast, s1 + 12, 18, (0, 0, 0), 8, TIP_M, (0, 0, 11))
lower(d_base, s1 + 24, 18, (0, 0, 0), 8, TIP_M, (0, 0, 0.8))
s2 = W("smaller", "and")
pop(tiny["root"], s2, 8, (0.45,) * 3)
key(M["top"], "location", s2 + 2, (0, 0, 24))
key(M["top"], "location", s2 + 12, (0, 0, 2))
for i, s_ in enumerate(M["secs"]):
    key(s_, "location", s2 + 2, (0, 0, 6 * i))
    key(s_, "location", s2 + 12, (0, 0, 0))
    key(s_, "scale", s2 + 2, (1, 1, 1))
    key(s_, "scale", s2 + 12, (1, 1, 0.33))
lower(M["jib"], s2 + 14, 16, (0, 0, 0), 18, TIP_T, (2, 0, 2), drop=60)
lower(M["cj"], s2 + 24, 16, (0, 0, 0), 30, TIP_T, (-5, 0, 1.5), drop=60)
lower(M["head"], s2 + 34, 16, (0, 0, 0), 26, TIP_T, (0, 0, 1), drop=60)
for i, s_ in enumerate(M["secs"]):
    lower(s_, s2 + 44 + i * 6, 12, (0, 0, 0), 24, TIP_T, (0, 0, 2), drop=60)
''')
R('''key(tiny["root"], "location", walk, (-5, -8, ROOF))''',
  '''# the swap to its small walking size happens exactly on the cut
key(tiny["root"], "location", walk - 1, (9, -8, ROOF))
key(tiny["root"], "scale", walk - 1, (0.45,) * 3)
key(tiny["root"], "location", walk, (-5, -8, ROOF))
key(tiny["root"], "scale", walk, (0.22,) * 3)''')
R("shot(a10, walk - 1, (0, (24, -40, ROOF + 12), (0, -2, ROOF + 5)), (1, (20, -38, ROOF + 10), (-2, -2, ROOF + 4)))",
  '''shot(a10, s0 - 1, (0, (0.5, -14.5, ROOF + 1.7), (7, -5, ROOF + 6)), (1, (0.2, -14.8, ROOF + 1.6), (7, -5, ROOF + 7)))
shot(s0, walk - 1, (0, (26, -46, ROOF + 15), (5, -3, ROOF + 9)), (1, (20, -38, ROOF + 10), (3, -4, ROOF + 4)))''')

# 11. the driver is actually seen climbing, and the skyscraper stops blocking the finale
R("vis(tower, (a8, LAST))", "vis(tower, (a8, a11 - 1))")
R("vis(lift, (a8, LAST))", "vis(lift, (a8, a11 - 1))")
R('''shot(a11, con - 1, (0, (-16, -40, 40), (-40, -22, 44)), (1, (-18, -42, 48), (-40, -22, 48)))''',
  '''shot(a11, cl0 - 1, (0, (-16, -40, 40), (-40, -22, 44)), (1, (-18, -42, 46), (-40, -22, 47)))
shot(cl0, con - 1, (0, (-35, -32, 27.6), (-40, -23, 27.6)), (1, (-34.5, -32, 42.6), (-40, -23, 43)))''')
R("(1, (6, -170, 44), (-16, 0, 66)))", "(1, (-8, -108, 30), (-34, -22, 42)))")

open("build_scene.py", "w", encoding="utf-8").write(s)

s = open("finish.py", encoding="utf-8").read()
s = s.replace("frames_v2", "frames_v3").replace("crane_short_v2", "crane_short_v3").replace("caps_v2", "caps_v3")
R("format=yuv420p[v];", "scale=out_range=tv,format=yuv420p[v];")
R('"-c:v", "libx264", "-crf", "17", "-preset", "medium",',
  '"-c:v", "libx264", "-crf", "17", "-preset", "medium", "-color_range", "tv",')
open("finish.py", "w", encoding="utf-8").write(s)
print("patched")
