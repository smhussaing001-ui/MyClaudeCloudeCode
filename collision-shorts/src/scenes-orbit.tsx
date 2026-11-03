import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import React, { useMemo } from "react";
import { useCurrentFrame } from "remotion";
import { Ctx, Scene, fontFamily as serif, glow, hexA, ripple, sphere } from "./kit";
import { FPS, H, W, smooth } from "./sims";
import {
  GEO,
  ROSE,
  WEAVES,
  Weave,
  geoEvents,
  geoPoint,
  orbitAngle,
  orbitsDone,
  progress,
  roseEvents,
  roseR,
  roseTable,
  weaveEvents,
} from "./sims-orbit";

const { fontFamily: sans } = loadInter("normal", { weights: ["500", "800"], subsets: ["latin"] });

const CX = 540;
const CY = 980;

const starfield = Array.from({ length: 150 }, (_, i) => {
  const f = (s: number) => {
    const v = Math.sin(i * s) * 43758.5453;
    return v - Math.floor(v);
  };
  return { x: f(127.1) * W, y: f(311.7) * H, s: f(74.7) };
});

const space = (c: Ctx) => {
  const g = c.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, "#060A1C");
  g.addColorStop(1, "#02030A");
  c.fillStyle = g;
  c.fillRect(0, 0, W, H);
  for (const s of starfield) {
    c.fillStyle = `rgba(230,236,255,${0.1 + 0.3 * s.s})`;
    c.beginPath();
    c.arc(s.x, s.y, 0.7 + 1.1 * s.s, 0, Math.PI * 2);
    c.fill();
  }
};

const fade = (c: Ctx, t: number) => {
  const a = Math.max(1 - smooth(0, 0.4, t), smooth(19.6, 20, t));
  if (a > 0) {
    c.fillStyle = `rgba(3,5,14,${a})`;
    c.fillRect(0, 0, W, H);
  }
};

const sun = (c: Ctx, x: number, y: number, r: number) => {
  glow(c, x, y, r * 4.5, "#FFC66E", 0.6);
  sphere(c, x, y, r, "#FFF8DC", "#FFD271", "#E5902E");
};

const planet = (c: Ctx, x: number, y: number, r: number, color: string) => {
  glow(c, x, y, r * 3.2, color, 0.55);
  sphere(c, x, y, r, "#FFFFFF", color, hexA(color, 0.7));
};

const Title: React.FC<{ text: string; children?: React.ReactNode }> = ({ text, children }) => {
  const t = useCurrentFrame() / FPS;
  return (
    <div
      style={{
        position: "absolute",
        top: 190,
        left: 70,
        right: 70,
        textAlign: "center",
        fontFamily: sans,
        fontWeight: 800,
        fontSize: 72,
        lineHeight: 1.14,
        textWrap: "balance",
        color: "#FFFFFF",
        opacity: smooth(0.1, 0.6, t),
      }}
    >
      {text}
      {children}
    </div>
  );
};

const EndLine: React.FC<{ text: string; from?: number }> = ({ text, from = 17.2 }) => {
  const t = useCurrentFrame() / FPS;
  return (
    <div
      style={{
        position: "absolute",
        top: 1490,
        left: 70,
        right: 70,
        textAlign: "center",
        fontFamily: sans,
        fontWeight: 500,
        fontSize: 50,
        color: "#EDF1FF",
        opacity: smooth(from, from + 0.7, t),
        translate: `0 ${(1 - smooth(from, from + 0.8, t)) * 14}px`,
      }}
    >
      {text}
    </div>
  );
};

// ---------- Line weaves ----------
const makeWeave = (w: Weave) => {
  const R = 450;
  const scale = R / w.b.au;
  const ra = w.a.au * scale;
  const rb = w.b.au * scale;
  const lines = new Float32Array(w.lines * 4);
  const buckets = new Uint8Array(w.lines);
  const BUCKETS = 24;
  for (let i = 0; i < w.lines; i++) {
    const y = (i / w.lines) * w.years;
    const a = orbitAngle(y, w.a.period);
    const b = orbitAngle(y, w.b.period);
    const x0 = CX + Math.cos(a) * ra;
    const y0 = CY + Math.sin(a) * ra;
    const x1 = CX + Math.cos(b) * rb;
    const y1 = CY + Math.sin(b) * rb;
    lines.set([x0, y0, x1, y1], i * 4);
    // Colour drifts with time, so neighbouring lines match and the weave reads as smooth sheets.
    buckets[i] = Math.floor((i / w.lines) * BUCKETS);
  }
  const events = weaveEvents(w);
  return { R, ra, rb, lines, buckets, BUCKETS, events };
};

const drawWeave = (w: Weave, d: ReturnType<typeof makeWeave>) => (c: Ctx, t: number) => {
  space(c);
  const p = progress(t);
  const years = p * w.years;
  const n = Math.floor(p * w.lines);

  c.strokeStyle = hexA(w.a.color, 0.28);
  c.lineWidth = 2;
  c.beginPath();
  c.arc(CX, CY, d.ra, 0, Math.PI * 2);
  c.stroke();
  c.strokeStyle = hexA(w.b.color, 0.32);
  c.beginPath();
  c.arc(CX, CY, d.rb, 0, Math.PI * 2);
  c.stroke();

  c.save();
  c.globalCompositeOperation = "lighter";
  c.lineWidth = 1.25;
  const settle = smooth(17, 18.5, t);
  for (let b = 0; b < d.BUCKETS; b++) {
    const u = b / (d.BUCKETS - 1);
    const hue = w.hue[0] + (w.hue[1] - w.hue[0]) * u;
    c.strokeStyle = `hsla(${hue},85%,${60 + 6 * settle}%,${0.24 + 0.08 * settle})`;
    c.beginPath();
    for (let i = 0; i < n; i++) {
      if (d.buckets[i] !== b) continue;
      c.moveTo(d.lines[i * 4], d.lines[i * 4 + 1]);
      c.lineTo(d.lines[i * 4 + 2], d.lines[i * 4 + 3]);
    }
    c.stroke();
  }
  c.restore();

  const a = orbitAngle(years, w.a.period);
  const b = orbitAngle(years, w.b.period);
  const ax = CX + Math.cos(a) * d.ra;
  const ay = CY + Math.sin(a) * d.ra;
  const bx = CX + Math.cos(b) * d.rb;
  const by = CY + Math.sin(b) * d.rb;
  c.strokeStyle = "rgba(255,255,255,0.75)";
  c.lineWidth = 2;
  c.beginPath();
  c.moveTo(ax, ay);
  c.lineTo(bx, by);
  c.stroke();
  for (const e of d.events) {
    const age = t - e.t;
    if (e.kind === "a") ripple(c, ax, ay, age, w.a.color, 70, 0.8);
    if (e.kind === "b") ripple(c, bx, by, age, w.b.color, 70, 0.8);
    if (e.kind === "meet") ripple(c, (ax + bx) / 2, (ay + by) / 2, age, "#FFFFFF", 130, 1.1);
  }
  sun(c, CX, CY, 22);
  planet(c, ax, ay, 13, w.a.color);
  planet(c, bx, by, 15, w.b.color);
  fade(c, t);
};

const Counter: React.FC<{ w: Weave }> = ({ w }) => {
  const t = useCurrentFrame() / FPS;
  const y = progress(t) * w.years;
  return (
    <div style={{ marginTop: 22, fontSize: 46, fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>
      <span style={{ color: w.a.color }}>{w.a.name}</span>
      <span style={{ color: "#FFFFFF", margin: "0 18px" }}>{orbitsDone(y, w.a.period, w.years)}</span>
      <span style={{ color: "rgba(255,255,255,0.55)" }}>:</span>
      <span style={{ color: "#FFFFFF", margin: "0 18px" }}>{orbitsDone(y, w.b.period, w.years)}</span>
      <span style={{ color: w.b.color }}>{w.b.name}</span>
    </div>
  );
};

const WeaveShort: React.FC<{ w: Weave }> = ({ w }) => {
  const draw = useMemo(() => drawWeave(w, makeWeave(w)), [w]);
  return (
    <Scene draw={draw} audio={`weave-${w.id}`}>
      <Title text={w.title}>
        <Counter w={w} />
      </Title>
      <EndLine text={w.end} />
    </Scene>
  );
};

export const VenusWeave = () => <WeaveShort w={WEAVES[0]} />;
export const SaturnWeave = () => <WeaveShort w={WEAVES[1]} />;
export const MarsWeave = () => <WeaveShort w={WEAVES[2]} />;

// ---------- Venus seen from Earth ----------
const GEO_STEPS = 1900;
const GEO_SCALE = 262;
const geoEv = geoEvents();
const geoTrace = Array.from({ length: GEO_STEPS + 1 }, (_, i) => geoPoint((i / GEO_STEPS) * GEO.years));

const drawGeo = (c: Ctx, t: number) => {
  space(c);
  const p = progress(t);
  const n = Math.floor(p * GEO_STEPS);
  const here = geoPoint(p * GEO.years);

  c.strokeStyle = "rgba(255,206,120,0.22)";
  c.lineWidth = 2;
  c.beginPath();
  c.arc(CX, CY, GEO_SCALE, 0, Math.PI * 2);
  c.stroke();

  c.save();
  c.globalCompositeOperation = "lighter";
  c.lineCap = "round";
  c.lineJoin = "round";
  const SEG = 60;
  for (const [width, alpha] of [[14, 0.09], [4, 0.95]] as const) {
    c.lineWidth = width;
    for (let i = 0; i < n; i += SEG) {
      const hue = 330 + 60 * (i / GEO_STEPS);
      c.strokeStyle = `hsla(${hue % 360},92%,70%,${alpha})`;
      c.beginPath();
      c.moveTo(CX + geoTrace[i].x * GEO_SCALE, CY + geoTrace[i].y * GEO_SCALE);
      for (let j = i + 1; j <= Math.min(n, i + SEG); j++) {
        c.lineTo(CX + geoTrace[j].x * GEO_SCALE, CY + geoTrace[j].y * GEO_SCALE);
      }
      c.stroke();
    }
  }
  c.restore();

  const vx = CX + here.x * GEO_SCALE;
  const vy = CY + here.y * GEO_SCALE;
  c.strokeStyle = "rgba(255,255,255,0.5)";
  c.lineWidth = 2;
  c.beginPath();
  c.moveTo(CX, CY);
  c.lineTo(vx, vy);
  c.stroke();
  for (const e of geoEv) {
    if (e.kind === "loop") ripple(c, vx, vy, t - e.t, "#FFD9EC", 150, 1.2);
  }
  sun(c, CX + here.sx * GEO_SCALE, CY + here.sy * GEO_SCALE, 18);
  planet(c, CX, CY, 17, "#79B8F2");
  planet(c, vx, vy, 13, "#F5C98B");
  fade(c, t);
};

const GeoFormula = () => (
  <div style={{ marginTop: 26, fontFamily: serif, fontWeight: 300, fontSize: 50, color: "#FFC6DF" }}>
    z(t) = 0.72 e<sup style={{ fontSize: 30 }}>1.63 it</sup> − e<sup style={{ fontSize: 30 }}>it</sup>
  </div>
);

export const VenusFromEarth = () => (
  <Scene draw={drawGeo} audio="geo">
    <Title text="Venus, seen from Earth">
      <GeoFormula />
    </Title>
    <EndLine text="Five loops, every 8 years." />
  </Scene>
);

// ---------- Mercury rosette ----------
const roseTab = roseTable();
const ROSE_SCALE = 355;
const roseEv = roseEvents();
const rosePts = Array.from({ length: ROSE.steps + 1 }, (_, i) => {
  const th = i * roseTab.dTheta;
  const r = roseR(th) * ROSE_SCALE;
  return { x: CX + r * Math.cos(th - Math.PI / 2), y: CY + r * Math.sin(th - Math.PI / 2) };
});

const roseIndex = (p: number) => {
  let lo = 0,
    hi = ROSE.steps;
  while (lo < hi) {
    const m = (lo + hi) >> 1;
    if (roseTab.cum[m] < p) lo = m + 1;
    else hi = m;
  }
  return lo;
};

const drawRose = (c: Ctx, t: number) => {
  space(c);
  const n = roseIndex(progress(t));
  c.save();
  c.globalCompositeOperation = "lighter";
  c.lineJoin = "round";
  const SEG = 90;
  for (const [width, alpha] of [[9, 0.05], [2.6, 0.85]] as const) {
    c.lineWidth = width;
    for (let i = 0; i < n; i += SEG) {
      c.strokeStyle = `hsla(${48 - 18 * (i / ROSE.steps)},100%,62%,${alpha})`;
      c.beginPath();
      c.moveTo(rosePts[i].x, rosePts[i].y);
      for (let j = i + 1; j <= Math.min(n, i + SEG); j++) c.lineTo(rosePts[j].x, rosePts[j].y);
      c.stroke();
    }
  }
  c.restore();
  const q = rosePts[n];
  for (const e of roseEv) ripple(c, q.x, q.y, t - e.t, "#FFE9A6", 60, 0.6);
  sun(c, CX, CY, 24);
  planet(c, q.x, q.y, 11, "#F2E3C0");
  fade(c, t);
};

const RoseFormula = () => (
  <div style={{ marginTop: 26, fontFamily: serif, fontWeight: 300, fontSize: 52, color: "#FFE28A" }}>
    r = 1 / (1 + 0.206 cos(24θ/25))
  </div>
);

export const MercuryRosette = () => (
  <Scene draw={drawRose} audio="rose">
    <Title text="Mercury's orbit slowly turns">
      <RoseFormula />
    </Title>
    <EndLine text="Real shape. Hugely sped up." />
  </Scene>
);
