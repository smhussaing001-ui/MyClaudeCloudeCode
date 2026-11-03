// Orbit geometry series: real orbital periods drawing patterns line by line.
import { type Ev, smooth } from "./sims.ts";

const DRAW_FROM = 1;
const DRAW_LEN = 16;

// Starts gently, then gathers speed, and settles as the pattern closes.
export const progress = (t: number) => {
  const u = Math.min(1, Math.max(0, (t - DRAW_FROM) / DRAW_LEN));
  return 0.6 * smooth(0, 1, u) + 0.4 * u;
};

export const timeOf = (p: number) => {
  let lo = DRAW_FROM,
    hi = DRAW_FROM + DRAW_LEN;
  for (let i = 0; i < 40; i++) {
    const m = (lo + hi) / 2;
    if (progress(m) < p) lo = m;
    else hi = m;
  }
  return hi;
};

export type Weave = {
  id: string;
  title: string;
  end: string;
  a: { name: string; period: number; au: number; color: string };
  b: { name: string; period: number; au: number; color: string };
  years: number;
  lines: number;
  hue: [number, number];
  folds: number;
};

export const WEAVES: Weave[] = [
  {
    id: "venus",
    title: "What do Venus and Earth draw?",
    end: "Five petals, every 8 years.",
    a: { name: "Venus", period: 0.6152, au: 0.723, color: "#F5C98B" },
    b: { name: "Earth", period: 1, au: 1, color: "#79B8F2" },
    years: 8,
    lines: 1100,
    hue: [320, 400],
    folds: 5,
  },
  {
    id: "saturn",
    title: "What do Jupiter and Saturn draw?",
    end: "Three meetings, every 59 years.",
    a: { name: "Jupiter", period: 11.862, au: 5.203, color: "#E9B98C" },
    b: { name: "Saturn", period: 29.457, au: 9.537, color: "#EEDD9E" },
    years: 59,
    lines: 1000,
    hue: [190, 270],
    folds: 3,
  },
  {
    id: "mars",
    title: "What do Earth and Mars draw?",
    end: "Seven turns, every 15 years.",
    a: { name: "Earth", period: 1, au: 1, color: "#79B8F2" },
    b: { name: "Mars", period: 1.8808, au: 1.524, color: "#EE8C6C" },
    years: 15.04,
    lines: 1200,
    hue: [135, 195],
    folds: 7,
  },
];

export const orbitAngle = (years: number, period: number) => -Math.PI / 2 + (2 * Math.PI * years) / period;

// Counts round up in the last moments because these periods close almost, not exactly.
export const orbitsDone = (years: number, period: number, totalYears: number) => {
  const v = years / period;
  const whole = Math.floor(totalYears / period + 0.03);
  return Math.min(whole, Math.floor(v + (years >= totalYears ? 0.03 : 0)));
};

export const weaveEvents = (w: Weave): Ev[] => {
  const out: Ev[] = [];
  const whole = (period: number) => Math.floor(w.years / period + 0.03);
  for (let k = 1; k <= whole(w.a.period); k++) {
    out.push({ t: timeOf(Math.min(1, (k * w.a.period) / w.years)), v: 1, i: k, kind: "a" });
  }
  for (let k = 1; k <= whole(w.b.period); k++) {
    out.push({ t: timeOf(Math.min(1, (k * w.b.period) / w.years)), v: 1, i: k, kind: "b" });
  }
  const syn = 1 / Math.abs(1 / w.a.period - 1 / w.b.period);
  for (let k = 1; k <= Math.floor(w.years / syn + 0.03); k++) {
    out.push({ t: timeOf(Math.min(1, (k * syn) / w.years)), v: 1, i: k, kind: "meet" });
  }
  return out.sort((p, q) => p.t - q.t);
};

// ---------- Venus as seen from Earth ----------
export const GEO = { years: 8, venusAU: 0.723, venusP: 0.6152 };

export const geoPoint = (years: number) => {
  const e = (2 * Math.PI * years) / 1;
  const v = (2 * Math.PI * years) / GEO.venusP;
  return {
    x: GEO.venusAU * Math.cos(v) - Math.cos(e),
    y: GEO.venusAU * Math.sin(v) - Math.sin(e),
    sx: -Math.cos(e),
    sy: -Math.sin(e),
  };
};

export const geoEvents = (): Ev[] => {
  const syn = 1 / (1 / GEO.venusP - 1);
  const out: Ev[] = [];
  for (let k = 0; k <= Math.floor(GEO.years / syn + 0.03); k++) {
    if (k > 0) out.push({ t: timeOf(Math.min(1, (k * syn) / GEO.years)), v: 1, i: k, kind: "loop" });
  }
  for (let k = 1; k <= 13; k++) out.push({ t: timeOf(Math.min(1, (k * GEO.venusP) / GEO.years)), v: 1, i: k, kind: "orbit" });
  return out.sort((p, q) => p.t - q.t);
};

// ---------- Mercury's ellipse, turning into a rosette ----------
export const ROSE = { e: 0.206, k: 24 / 25, turns: 25, steps: 7000 };
export const roseR = (theta: number) => 1 / (1 + ROSE.e * Math.cos(ROSE.k * theta));

// Equal areas in equal times: the planet hurries near the Sun, as Kepler's second law says.
export const roseTable = () => {
  const { steps, turns } = ROSE;
  const dTheta = (turns * 2 * Math.PI) / steps;
  const cum = new Float64Array(steps + 1);
  for (let i = 1; i <= steps; i++) {
    const r = roseR((i - 0.5) * dTheta);
    cum[i] = cum[i - 1] + r * r * dTheta;
  }
  const total = cum[steps];
  for (let i = 0; i <= steps; i++) cum[i] /= total;
  return { cum, dTheta };
};

export const roseEvents = (): Ev[] => {
  const { cum, dTheta } = roseTable();
  const out: Ev[] = [];
  for (let m = 1; m <= 24; m++) {
    const theta = (2 * Math.PI * m) / ROSE.k;
    const idx = Math.min(ROSE.steps, Math.round(theta / dTheta));
    out.push({ t: timeOf(cum[idx]), v: 1, i: m, kind: "perihelion" });
  }
  return out;
};
