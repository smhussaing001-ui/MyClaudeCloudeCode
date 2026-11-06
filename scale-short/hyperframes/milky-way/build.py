#!/usr/bin/env python3
"""
Generate the HyperFrames composition files for the Milky Way short.

Dot positions for every diagram are computed HERE, at build time, and written
into the HTML as static SVG. The HyperFrames contract forbids unseeded
Math.random() in a composition; pre-computing removes runtime randomness
entirely rather than relying on a seeded PRNG at render time.

Palette, timings and the accent are the measured values from ../../STYLE-SPEC.md.
"""
import math, os, json

W, H = 1080, 1920
HOLD, SLIDE = 5.0, 0.5
ACCENT = "#ED4839"
DARK = "#030303"
PAPER = "#EFEFE8"
WHITE = "#FFFFFF"

# Vertical band the HyperFrames vertical guide allows: nothing above 168,
# everything readable above 1330.
TOP, BOT = 168, 1330

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "compositions")


class R:
    """Deterministic PRNG (mulberry32), so a rebuild gives identical output."""
    def __init__(self, s): self.s = s & 0xFFFFFFFF
    def __call__(self):
        self.s = (self.s + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.s
        t = (t ^ (t >> 15)) * (1 | t) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) & 0xFFFFFFFF ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296


def sphere_dots(size, seed, blobs=13):
    r = size / 2
    rnd = R(seed)
    out = []
    SP = size * 0.0165
    for b in range(blobs):
        pa = ((b + rnd() * 0.85) / blobs) * math.tau
        pd = (0.18 + math.sqrt(rnd()) * 0.52) * r
        cx, cy = r + math.cos(pa) * pd, r + math.sin(pa) * pd
        rad = r * (0.13 + rnd() * 0.19)
        w1, w2 = 0.24 + rnd() * 0.3, 0.12 + rnd() * 0.22
        ph = rnd() * 6.28
        lobes = 2 + int(rnd() * 3)
        shape = lambda a: rad * (1 + w1 * math.sin(a * lobes + ph) + w2 * math.sin(a * (lobes + 2) - ph))
        per, px, py = 0.0, cx + shape(0), cy
        for k in range(1, 161):
            a = k / 160 * math.tau
            x, y = cx + math.cos(a) * shape(a), cy + math.sin(a) * shape(a)
            per += math.hypot(x - px, y - py); px, py = x, y
        n = max(12, round(per / SP))
        for i in range(n):
            a = i / n * math.tau
            x, y = cx + math.cos(a) * shape(a), cy + math.sin(a) * shape(a)
            if math.hypot(x - r, y - r) < r * 0.93:
                out.append((x, y))
    return out


def spiral_dots(size, seed, arms=4):
    r = size / 2
    rnd = R(seed)
    pts, core = [], []
    B, TURN = 0.26, 2.5
    marker = (r, r)
    for a in range(arms):
        off = a / arms * math.tau
        for i in range(241):
            t = i / 240
            th = t * TURN * math.pi
            rad = r * 0.1 * math.exp(B * th)
            if rad > r * 0.95: break
            spread = size * (0.003 + t * 0.03)
            jx, jy = (rnd() - 0.5) * spread * 2, (rnd() - 0.5) * spread * 2
            x, y = r + math.cos(th + off) * rad + jx, r + math.sin(th + off) * rad + jy
            if math.hypot(x - r, y - r) < r * 0.97:
                pts.append((x, y, t, 0.5 + rnd() * 0.5))
            if a == 1 and abs(t - 0.8) < 1 / 240:
                marker = (r + math.cos(th + off) * rad, r + math.sin(th + off) * rad)
    for _ in range(85):
        a2, d2 = rnd() * math.tau, (rnd() ** 2.3) * r * 0.13
        core.append((r + math.cos(a2) * d2, r + math.sin(a2) * d2 * 0.88, 0.45 + rnd() * 0.55))
    return pts, core, marker


def contour_paths(w, h, seed, rings=26):
    rnd = R(seed)
    cx, cy = w / 2, h * 0.46
    ph = [rnd() * 6.28 for _ in range(3)]
    paths = []
    for i in range(rings):
        base = (i + 1) * (w / rings) * 0.56
        d = []
        for k in range(91):
            a = k / 90 * math.tau
            rr = base * (1 + 0.12 * math.sin(a * 2 + ph[0] + i * 0.12)
                         + 0.07 * math.sin(a * 3 - ph[1] - i * 0.08)
                         + 0.04 * math.sin(a * 5 + ph[2]))
            d.append(f"{'M' if k==0 else 'L'}{cx+math.cos(a)*rr:.1f},{cy+math.sin(a)*rr*0.82:.1f}")
        paths.append("".join(d) + "Z")
    return paths


def starburst_svg(size, color, spokes=12, cls=""):
    r = size / 2
    sw = max(1, size * 0.052)
    inner, outer = r * 0.08, r * 0.92
    lines = []
    for i in range(spokes):
        a = i / spokes * math.tau - math.pi / 2
        lines.append(
            f'<line class="{cls}" x1="{r+math.cos(a)*inner:.1f}" y1="{r+math.sin(a)*inner:.1f}" '
            f'x2="{r+math.cos(a)*outer:.1f}" y2="{r+math.sin(a)*outer:.1f}" '
            f'stroke="{color}" stroke-width="{sw:.1f}" stroke-linecap="round"/>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{"".join(lines)}</svg>'


def ruler_svg(width, playhead_from, playhead_to, datum, datum_at, ticks=56):
    """Rule at the top of the band with ticks hanging down, as measured."""
    Hh = width * 0.1
    base = Hh * 0.16
    minor, major = Hh * 0.17, Hh * 0.36
    hair = max(1, width * 0.0019)
    p = [f'<line x1="0" y1="{base:.1f}" x2="{width}" y2="{base:.1f}" stroke="{WHITE}" stroke-width="{hair:.1f}"/>',
         f'<line x1="{hair:.1f}" y1="{base-major*0.75:.1f}" x2="{hair:.1f}" y2="{base+major:.1f}" stroke="{WHITE}" stroke-width="{hair:.1f}"/>']
    for i in range(ticks):
        x = i / (ticks - 1) * width
        t = minor * 1.55 if i % 5 == 0 else minor
        p.append(f'<line x1="{x:.1f}" y1="{base:.1f}" x2="{x:.1f}" y2="{base+t:.1f}" stroke="{WHITE}" stroke-width="{hair:.1f}"/>')
    p.append(f'<line x1="{datum_at*width:.1f}" y1="{base-major*0.55:.1f}" x2="{datum_at*width:.1f}" y2="{base+major:.1f}" stroke="{WHITE}" stroke-width="{hair:.1f}"/>')
    head = (f'<g class="playhead"><line x1="0" y1="{base:.1f}" x2="0" y2="{base+major*1.5:.1f}" '
            f'stroke="{ACCENT}" stroke-width="{hair*1.8:.1f}"/>'
            f'<circle cx="0" cy="{base:.1f}" r="{width*0.0185:.1f}" fill="{ACCENT}"/></g>')
    return (f'<svg class="ruler" width="{width}" height="{Hh*1.25:.0f}" style="overflow:visible">'
            f'{"".join(p)}{head}</svg>'), base, Hh


def odometer_html(value, size, max_width):
    """Digit drums. Each digit is a clipped column that GSAP rolls into place."""
    DIGIT, SEP = 0.56, 0.3
    em = sum(DIGIT if c.isdigit() else SEP for c in value)
    if em * size > max_width:
        size = max_width / em
    out, di = [], 0
    for ch in value:
        if not ch.isdigit():
            out.append(f'<span class="sep" style="width:{size*SEP:.1f}px">{ch}</span>')
            continue
        col = "".join(f'<span class="d">{d%10}</span>' for d in range(11))
        out.append(
            f'<span class="drum" data-layout-allow-overflow data-target="{ch}" data-order="{di}" '
            f'style="width:{size*DIGIT:.1f}px;height:{size:.1f}px">'
            f'<span class="col" style="--dh:{size:.1f}px">{col}</span></span>')
        di += 1
    return f'<div class="odo" style="font-size:{size:.1f}px;--dh:{size:.1f}px">{"".join(out)}</div>', size


# ---------------------------------------------------------------- the beats
L = lambda t: {"kind": "light", "caption": t}
def D(**k): k["kind"] = "dark"; return k

BEATS = [
    L("Tonight, look up."),
    D(index="01", label="YOU", unit="PLANET", value="1",
      caption="You're on one planet.", ph=(0.0, 0.05), datum="HERE", datum_at=0.06,
      seed=31, visual="sphere", prog=0.04),
    D(index="02", label="THE SUN", unit="LIGHT MINUTES", value="8",
      caption="Eight minutes of light away.", ph=(0.05, 0.16), datum="SUN", datum_at=0.16,
      seed=42, visual="sphere", prog=0.10),
    L("Now keep going."),
    D(index="03", label="NEXT STAR", unit="LIGHT YEARS", value="4.2",
      caption="The next one takes four years.", ph=(0.16, 0.31), datum="PROXIMA", datum_at=0.31,
      seed=17, visual="sphere", prog=0.20),
    D(index="04", label="THE DISC", unit="LIGHT YEARS ACROSS", value="100,000",
      caption="A hundred thousand across.", ph=(0.31, 0.62), datum="SUN", datum_at=0.62,
      seed=5, visual="spiral", prog=0.30),
    L("That's where you live."),
    D(index="05", label="THE COUNT", unit="STARS", value="400,000,000,000",
      caption="Nobody has counted them.", ph=(0.62, 0.74), datum="EST.", datum_at=0.5,
      seed=9, visual="spiral", marker=False, prog=0.38),
    L("We are not in the middle."),
    D(index="06", label="OFF CENTRE", unit="LIGHT YEARS OUT", value="26,000",
      caption="Out on a quiet arm.", ph=(0.74, 0.45), datum="CORE", datum_at=0.07,
      seed=5, visual="spiral", prog=0.50),
    D(index="07", label="THE CENTRE", unit="SOLAR MASSES", value="4,300,000",
      caption="Something sits at the centre.", ph=(0.45, 0.08), datum="SGR A*", datum_at=0.08,
      seed=13, visual="contour", prog=0.58),
    D(index="08", label="THE ORBIT", unit="YEARS PER LAP", value="225,000,000",
      caption="One lap: 225 million years.", ph=(0.08, 0.52), datum="ONE LAP", datum_at=0.52,
      seed=5, visual="spiral", prog=0.66),
    L("We've been here before."),
    D(index="09", label="LAST LAP", unit="YEARS AGO", value="230,000,000",
      caption="Last time: dinosaurs.", ph=(0.52, 0.12), datum="NOW", datum_at=0.93,
      seed=21, visual="contour", prog=0.78),
    D(index="10", label="INBOUND", unit="YEARS FROM NOW", value="4,500,000,000",
      caption="Andromeda is coming.", ph=(0.12, 0.88), datum="NOW", datum_at=0.07,
      seed=29, visual="contour", prog=0.90),
    L("You're on it."),
]
# slide direction flips where the narration turns
FLIP = {8, 13}


SHARED_CSS = f"""
    #root {{ position:absolute; inset:0; overflow:hidden; }}
    .stage {{ position:absolute; inset:0; }}
    .band {{ position:absolute; left:81px; right:81px; top:{TOP}px; bottom:{H-BOT}px;
             display:flex; flex-direction:column; }}
    .chrome {{ display:flex; align-items:flex-start; justify-content:space-between; }}
    .sect {{ font-family:'JetBrains Mono',monospace; font-size:28px; letter-spacing:6.5px;
             color:{WHITE}; opacity:.85; white-space:nowrap; }}
    .figwrap {{ flex:1; display:flex; align-items:flex-end; justify-content:center; min-height:0; }}
    .rulerwrap {{ margin:0 -81px 24px; }}
    .unitrow {{ display:flex; align-items:center; gap:32px; }}
    .approx {{ font-family:'League Gothic',sans-serif; font-size:67px; color:{ACCENT}; line-height:.8; }}
    .unit {{ font-family:'JetBrains Mono',monospace; font-size:32px; letter-spacing:13px;
             color:{PAPER}; white-space:nowrap; }}
    .odo {{ display:flex; align-items:flex-end; font-family:'League Gothic',sans-serif;
            line-height:1; color:{PAPER}; font-variant-numeric:tabular-nums; }}
    .drum {{ display:inline-block; overflow:hidden; position:relative; }}
    .drum .col {{ position:absolute; left:0; top:0; display:flex; flex-direction:column;
                  align-items:center; width:100%; }}
    .drum .d {{ height:var(--dh); line-height:1; display:block; }}
    .sep {{ display:inline-block; text-align:center; line-height:1; }}
    .cap {{ display:flex; align-items:center; gap:30px; margin-top:34px; }}
    .cap .txt {{ font-family:Inter,sans-serif; font-weight:700; font-size:58px; }}
    .datum {{ position:absolute; font-family:'JetBrains Mono',monospace; font-size:30px;
              letter-spacing:6.5px; color:{WHITE}; white-space:nowrap; transform:translateX(-50%); }}
"""


def dark_scene(i, b):
    cid = f"s{i:02d}"
    size = int(W * 0.66)
    fig = ""
    if b["visual"] == "sphere":
        dots = sphere_dots(size, b["seed"])
        r = size / 2
        circ = 2 * math.pi * (r * 0.96)
        fig = (f'<svg class="fig" width="{size}" height="{size}" style="overflow:visible">'
               f'<circle class="arc" cx="{r}" cy="{r}" r="{r*0.96:.1f}" fill="none" stroke="{WHITE}" '
               f'stroke-width="{size*0.0085:.1f}" stroke-linecap="round" '
               f'stroke-dasharray="{circ*0.82:.1f} {circ:.1f}" stroke-dashoffset="{circ*0.82:.1f}" '
               f'transform="rotate(-95 {r} {r})"/>'
               + "".join(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="{size*0.0062:.2f}" fill="{WHITE}" opacity="0"/>' for x, y in dots)
               + f'<circle class="here" cx="{r}" cy="{r}" r="{size*0.016:.1f}" fill="{ACCENT}" opacity="0"/></svg>')
    elif b["visual"] == "spiral":
        ssz = int(size * 1.12)
        pts, core, mk = spiral_dots(ssz, b["seed"])
        parts = [f'<circle class="cdot" cx="{x:.1f}" cy="{y:.1f}" r="{ssz*0.0063:.2f}" fill="{WHITE}" opacity="0" data-o="{o:.2f}"/>' for x, y, o in core]
        for x, y, t, o in pts:
            parts.append(f'<circle class="sdot" cx="{x:.1f}" cy="{y:.1f}" r="{ssz*0.0055:.2f}" fill="{WHITE}" opacity="0" data-t="{t:.3f}" data-o="{o:.2f}"/>')
        if b.get("marker", True):
            parts.append(f'<g class="mk" opacity="0"><circle cx="{mk[0]:.1f}" cy="{mk[1]:.1f}" r="{ssz*0.014:.1f}" fill="{ACCENT}"/>'
                         f'<circle cx="{mk[0]:.1f}" cy="{mk[1]:.1f}" r="{ssz*0.045:.1f}" fill="none" stroke="{ACCENT}" stroke-width="{ssz*0.0035:.1f}" opacity=".65"/></g>')
        fig = f'<svg class="fig" width="{ssz}" height="{ssz}" style="overflow:visible">{"".join(parts)}</svg>'
    else:  # contour, sits behind everything
        paths = contour_paths(W, H, b["seed"])
        fig = ""
        contour = ('<svg class="contour" width="%d" height="%d">' % (W, H)) + "".join(
            f'<path d="{d}" fill="none" stroke="{"#8E2B22" if k%7==3 else "#2A2A2A"}" '
            f'stroke-width="1.5" opacity="0"/>' for k, d in enumerate(paths)) + "</svg>"

    contour_layer = contour if b["visual"] == "contour" else ""
    if b["visual"] == "sphere":
        figtweens = (
            f"      tl.fromTo('#{cid} .arc', {{ strokeDashoffset: (i, t) => t.getAttribute('stroke-dasharray').split(' ')[0] }},\n"
            f"        {{ strokeDashoffset: 0, duration: 2.4, ease: 'power2.out' }}, 0.13);\n"
            f"      tl.fromTo('#{cid} .dot', {{ opacity: 0 }}, {{ opacity: 1, duration: 0.01, stagger: {{ amount: 3.1 }} }}, 0.13);\n"
            f"      tl.fromTo('#{cid} .here', {{ opacity: 0 }}, {{ opacity: 1, duration: 0.5 }}, 1.6);")
    elif b["visual"] == "spiral":
        mk = (f"\n      tl.fromTo('#{cid} .mk', {{ opacity: 0, scale: 1.5, transformOrigin: 'center' }},\n"
              f"        {{ opacity: 1, scale: 1, duration: 0.6, ease: 'power3.out' }}, 2.7);") if b.get("marker", True) else ""
        figtweens = (
            f"      tl.fromTo('#{cid} .cdot', {{ opacity: 0 }}, {{ opacity: (i, t) => +t.dataset.o, duration: 0.5 }}, 0.13);\n"
            f"      q('.sdot').forEach((el) => {{\n"
            f"        tl.fromTo(el, {{ opacity: 0 }}, {{ opacity: +el.dataset.o, duration: 0.01 }}, 0.13 + (+el.dataset.t) * 3.2);\n"
            f"      }});" + mk)
    else:
        figtweens = (
            f"      tl.fromTo('#{cid} .contour path', {{ opacity: 0 }},\n"
            f"        {{ opacity: (i) => (i % 7 === 3 ? 0.55 : 0.75), duration: 1.2, stagger: 0.012, ease: 'power2.out' }}, 0.1);")
    rsvg, rbase, rH = ruler_svg(W * 1.06, b["ph"][0], b["ph"][1], b["datum"], b["datum_at"])
    odo, osize = odometer_html(b["value"], W * 0.3, W * 0.86)
    burst = starburst_svg(40, ACCENT, 12, "sp")
    # the rule bleeds past the frame, so a datum near either end would clip:
    # keep the label itself inside the safe area while its tick stays put
    datum_x = min(max(b["datum_at"] * W * 1.06, 110), W - 110)
    label = f'{b["index"]}  /  {b["label"]}'

    return cid, f"""<template>
  <style>
    {SHARED_CSS}
    #root .contour {{ position:absolute; left:0; top:0; }}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}"
       style="background:{DARK}">
    <div class="stage" id="{cid}-stage" data-layout-allow-overflow>
      {contour_layer}
      <div class="band" id="{cid}-band">
        <div class="chrome">
          <div class="sect" id="{cid}-sect">{label}</div>
          <svg width="238" height="32" style="overflow:visible">
            <line x1="0" y1="13" x2="238" y2="13" stroke="{WHITE}" stroke-width="2"/>
            <line x1="{b['prog']*238:.0f}" y1="4" x2="{b['prog']*238:.0f}" y2="23" stroke="{ACCENT}" stroke-width="4"/>
          </svg>
        </div>
        <div class="figwrap" style="margin-bottom:-36px">{fig}</div>
        <div class="rulerwrap" style="position:relative">
          {rsvg}
          <div class="datum" style="left:{datum_x:.0f}px; top:{rbase+rH*0.36+rH*0.1:.0f}px">{b['datum']}</div>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          <div class="unitrow"><span class="approx">&#8776;</span><span class="unit">{b['unit']}</span></div>
          {odo}
        </div>
        <div class="cap" id="{cid}-cap"><span class="burst">{burst}</span><span class="txt" style="color:{PAPER}">{b['caption']}</span></div>
      </div>
    </div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      const q = (s) => Array.from(document.querySelectorAll('#{cid} ' + s));
      const W = {W * 1.06};
      // slow push: the reference is never perfectly frozen
      tl.fromTo('#{cid}-stage', {{ scale: 1 }}, {{ scale: 1.07, duration: {HOLD}, ease: 'none' }}, 0);
      tl.fromTo('#{cid}-stage', {{ y: -6 }}, {{ y: 6, duration: {HOLD}, ease: 'sine.inOut' }}, 0);
{figtweens}
      tl.fromTo('#{cid} .playhead', {{ x: {b['ph'][0]} * W }}, {{ x: {b['ph'][1]} * W, duration: 2.5, ease: 'power3.inOut' }}, 0.33);
      q('.drum').forEach((el) => {{
        const col = el.querySelector('.col');
        const target = +el.dataset.target, order = +el.dataset.order;
        const total = 2 * 10 + target;
        const t0 = 0.2 + order * 0.133;
        tl.fromTo(col, {{ y: 0, filter: 'blur(0px)' }},
          {{ y: -(total % 10) * {osize:.1f} - 0 * {osize:.1f}, duration: 1.85, ease: 'power3.out' }}, t0);
        tl.fromTo(col, {{ filter: 'blur(0px)' }}, {{ filter: 'blur({osize*0.07:.1f}px)', duration: 0.5, ease: 'power1.out' }}, t0);
        tl.to(col, {{ filter: 'blur(0px)', duration: 0.8, ease: 'power2.in' }}, t0 + 0.9);
      }});
      tl.fromTo('#{cid}-cap', {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.45, ease: 'power3.out' }}, 0.87);
      tl.fromTo('#{cid} .sp', {{ scaleX: 0.1, scaleY: 0.1, transformOrigin: 'center' }},
        {{ scaleX: 1, scaleY: 1, duration: 0.5, ease: 'power3.out' }}, 0.87);
      window.__timelines['{cid}'] = tl;
    }})();
  </script>
</template>
"""


def light_scene(i, b):
    cid = f"s{i:02d}"
    burst = starburst_svg(int(W * 0.3), ACCENT, 12, "sp")
    cap_burst = starburst_svg(40, ACCENT, 12, "cb")
    return cid, f"""<template>
  <style>
    {SHARED_CSS}
    #root .sky {{ position:absolute; inset:0;
      background:linear-gradient(180deg,#EBEBEB 0%,#DCDCDC 62%,#D4D4D4 100%); }}
    #root .floor {{ position:absolute; left:0; right:0; top:{int(H*0.68)}px; bottom:0;
      background:linear-gradient(180deg,rgba(0,0,0,0) 0%,rgba(0,0,0,.045) 100%); }}
    #root .mark {{ position:absolute; left:0; right:0; top:{TOP}px; bottom:{H-BOT}px;
      display:flex; align-items:center; justify-content:center; }}
    #root .lcap {{ position:absolute; left:81px; top:{BOT-96}px; display:flex;
      align-items:center; gap:30px; }}
  </style>
  <div id="root" data-composition-id="{cid}" data-width="{W}" data-height="{H}"
       style="background:linear-gradient(180deg,#EBEBEB 0%,#DCDCDC 62%,#D4D4D4 100%)">
    <div class="stage" id="{cid}-stage" data-layout-allow-overflow>
      <div class="sky"></div>
      <div class="floor"></div>
      <div class="mark" id="{cid}-mark">{burst}</div>
      <div class="lcap" id="{cid}-cap">
        <span>{cap_burst}</span>
        <span class="txt" style="font-family:Inter,sans-serif;font-weight:700;font-size:58px;color:#1A1A1A">{b['caption']}</span>
      </div>
    </div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      tl.fromTo('#{cid}-stage', {{ scale: 1 }}, {{ scale: 1.07, duration: {HOLD}, ease: 'none' }}, 0);
      tl.fromTo('#{cid}-stage', {{ y: -7 }}, {{ y: 7, duration: {HOLD}, ease: 'sine.inOut' }}, 0);
      tl.fromTo('#{cid} .sp', {{ scaleX: 0.06, scaleY: 0.06, transformOrigin: 'center' }},
        {{ scaleX: 1, scaleY: 1, duration: 2.0, ease: 'power3.out' }}, 0.13);
      tl.fromTo('#{cid}-cap', {{ opacity: 0, y: 14 }},
        {{ opacity: 1, y: 0, duration: 0.45, ease: 'power3.out' }}, 1.0);
      tl.fromTo('#{cid} .cb', {{ scaleX: 0.1, scaleY: 0.1, transformOrigin: 'center' }},
        {{ scaleX: 1, scaleY: 1, duration: 0.5, ease: 'power3.out' }}, 1.0);
      window.__timelines['{cid}'] = tl;
    }})();
  </script>
</template>
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    hosts, scripts = [], []
    total = (len(BEATS) - 1) * (HOLD - SLIDE) + HOLD
    for i, b in enumerate(BEATS):
        cid, html = (light_scene(i, b) if b["kind"] == "light" else dark_scene(i, b))
        open(os.path.join(OUT, f"{cid}.html"), "w", encoding="utf-8").write(html)
        start = i * (HOLD - SLIDE)
        hosts.append(
            f'      <div id="{cid}" data-composition-id="{cid}" '
            f'data-composition-src="compositions/{cid}.html" data-start="{start:.2f}" '
            f'data-duration="{HOLD}" data-track-index="1" data-track-kind="graphics" '
            f'data-width="{W}" data-height="{H}" style="z-index:{i+1}"></div>')
        # No cuts anywhere: each scene slides in, and the one under it slides out.
        # Direction flips at the two turns in the narration.
        down = i in FLIP
        sign = "-" if down else ""
        if i > 0:
            scripts.append(
                f"  tl.fromTo('#{cid}', {{ yPercent: {sign}100 }}, "
                f"{{ yPercent: 0, duration: {SLIDE}, ease: 'power2.inOut' }}, {start:.2f});")
        prev_down = (i + 1) in FLIP
        if i < len(BEATS) - 1:
            out_sign = "" if prev_down else "-"
            scripts.append(
                f"  tl.to('#{cid}', {{ yPercent: {out_sign}100, duration: {SLIDE}, "
                f"ease: 'power2.inOut' }}, {start + HOLD - SLIDE:.2f});")

    index = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/js/gsap.min.js"></script>
    <style>
      * {{ margin:0; padding:0; box-sizing:border-box; }}
      html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:{DARK}; }}
      #root {{ width:100%; height:100%; position:relative; overflow:hidden; }}
      #root > div[data-composition-src] {{ position:absolute; inset:0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.2f}"
         data-width="{W}" data-height="{H}">
{chr(10).join(hosts)}
    </div>
    <script>
      // The reference has zero hard cuts across its whole runtime. Scenes are
      // overlapped by the slide length and pushed vertically: the incoming
      // scene slides in while the one beneath it slides out.
      const tl = gsap.timeline({{ paused: true }});
{chr(10).join(scripts)}
      window.__timelines['main'] = tl;
    </script>
  </body>
</html>
"""
    open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(index)
    print(f"wrote index.html + {len(BEATS)} scenes, duration {total:.2f}s")


if __name__ == "__main__":
    main()
