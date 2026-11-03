// Solar system series: every scene is a collision story built on a geometric progression.
import { type Ev, smooth } from "./sims.ts";

const rng = (seed: number) => () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let r = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
  return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
};

// ---------- 1. Titius-Bode: gaps between orbits roughly double ----------
export const BODE = [
  { name: "Mercury", pred: 0.4, real: 0.39, r: 15, c: "#B9AFA4" },
  { name: "Venus", pred: 0.7, real: 0.72, r: 22, c: "#E7CFA0" },
  { name: "Earth", pred: 1.0, real: 1.0, r: 23, c: "#6FA8DC" },
  { name: "Mars", pred: 1.6, real: 1.52, r: 18, c: "#D9775A" },
  { name: "Ceres", pred: 2.8, real: 2.77, r: 12, c: "#A9A39B" },
  { name: "Jupiter", pred: 5.2, real: 5.2, r: 46, c: "#DDB48C" },
  { name: "Saturn", pred: 10, real: 9.58, r: 40, c: "#E8D5A3" },
  { name: "Uranus", pred: 19.6, real: 19.2, r: 30, c: "#9FDCE0" },
  { name: "Neptune", pred: 38.8, real: 30.05, r: 30, c: "#6C8FE8" },
];
const BODE_START = 1.1;
const BODE_STEP = 2.08;
export const bodeHit = (k: number) => BODE_START + k * BODE_STEP;
export const bodeAngle = (k: number) => ((-90 + k * 47) * Math.PI) / 180;

export const bodeEvents = (): Ev[] => BODE.map((p, i) => ({ t: bodeHit(i), v: 1, i, kind: "planet" }));

// World position of the comet, and the camera's AU radius (which zooms out geometrically).
export const bodeState = (t: number) => {
  const planetXY = (k: number) => ({ x: BODE[k].real * Math.cos(bodeAngle(k)), y: BODE[k].real * Math.sin(bodeAngle(k)) });
  if (t <= bodeHit(0)) {
    const u = smooth(0, bodeHit(0), t);
    const p = planetXY(0);
    return { x: p.x * u, y: p.y * u, R: 0.39 };
  }
  const k = Math.min(BODE.length - 1, Math.floor((t - BODE_START) / BODE_STEP));
  if (k === BODE.length - 1) {
    const p = planetXY(k);
    return { x: p.x, y: p.y, R: BODE[k].real };
  }
  const u = (t - bodeHit(k)) / BODE_STEP;
  const e = smooth(0, 1, u);
  const a = planetXY(k);
  const b = planetXY(k + 1);
  return {
    x: a.x + (b.x - a.x) * e,
    y: a.y + (b.y - a.y) * e,
    R: Math.exp(Math.log(BODE[k].real) + (Math.log(BODE[k + 1].real) - Math.log(BODE[k].real)) * e),
  };
};

// ---------- 2. Laplace resonance: Io, Europa, Ganymede orbit 4 : 2 : 1 ----------
export const MOONS = [
  { name: "Io", period: 1.5, phase: 0, ring: 205, r: 19, c: "#F0CF6A" },
  { name: "Europa", period: 3, phase: 0, ring: 305, r: 17, c: "#DCE6EE" },
  // Phase 90 degrees satisfies the real relation L1 - 3 L2 + 2 L3 = 180 degrees,
  // which is why the three moons never line up together.
  { name: "Ganymede", period: 6, phase: 90, ring: 415, r: 24, c: "#B3A595" },
];
export const LAPLACE_T0 = 1;
export const moonAngle = (m: (typeof MOONS)[number], t: number) => ((t - LAPLACE_T0) / m.period) * 360 + m.phase;

export const laplaceEvents = (): Ev[] => {
  const out: Ev[] = [];
  MOONS.forEach((m, i) => {
    const first = (((360 - m.phase) % 360) / 360) * m.period + LAPLACE_T0;
    for (let t = first; t < 19.4; t += m.period) out.push({ t, v: 1, i, kind: "pin" });
  });
  return out.sort((a, b) => a.t - b.t);
};

// ---------- 3. Asteroids: width x2, mass and energy x8 ----------
export const ROCK_COUNT = 8;
export const rockHit = (k: number) => 1.6 + k * 2.3;
export const rockX = (k: number) => {
  let x = 0;
  for (let i = 1; i <= k; i++) x += (i % 2 ? 1 : -1) * 1.15 * 2 ** i;
  return x;
};
export const asteroidEvents = (): Ev[] =>
  Array.from({ length: ROCK_COUNT }, (_, i) => ({ t: rockHit(i), v: 1, i, kind: "impact" }));

export const rockDust = (k: number) => {
  const rand = rng(100 + k);
  return Array.from({ length: 34 }, () => ({
    vx: (rand() - 0.5) * 3.6,
    vy: 0.8 + rand() * 2.4,
    size: 0.015 + rand() * 0.035,
  }));
};

// ---------- 4. Accretion: 64, 32, 16, 8, 4, 2, 1 ----------
export const ACC = { rounds: 6, start: 1, step: 2.72, ring: 345 };

export type Merge = { a: number; b: number; mid: number; hit: number; start: number; m: number; round: number };

export const accretionSim = () => {
  const rand = rng(64);
  let bodies = Array.from({ length: 64 }, (_, i) => ({ angle: (i / 64) * Math.PI * 2, m: 1 }));
  const rounds: Merge[][] = [];
  const events: Ev[] = [];
  for (let r = 0; r < ACC.rounds; r++) {
    const start = ACC.start + r * ACC.step;
    const merges: Merge[] = [];
    const next: typeof bodies = [];
    for (let k = 0; k < bodies.length; k += 2) {
      const a = bodies[k];
      const b = bodies[k + 1];
      const hit = start + 1.0 + rand() * 1.1 * (1 - r / ACC.rounds);
      const mid = (a.angle + b.angle) / 2;
      merges.push({ a: a.angle, b: b.angle, mid, hit, start, m: a.m, round: r });
      next.push({ angle: mid, m: a.m * 2 });
      events.push({ t: hit, v: 1, i: r, kind: "merge", x: Math.cos(mid) });
    }
    rounds.push(merges);
    bodies = next;
  }
  events.sort((p, q) => p.t - q.t);
  return { rounds, events, final: bodies[0] };
};

// ---------- 5. Moon bounce: every bounce reaches half the height ----------
export const MOON_G = 1.62;
export const DROP_M = 8;
export const BOUNCE_E = Math.SQRT1_2;
const FALL = Math.sqrt((2 * DROP_M) / MOON_G);
export const BOUNCE_START = 0.7;

export const bounceSim = () => {
  const segs: { t0: number; dur: number; h: number; apex: boolean }[] = [];
  const events: Ev[] = [];
  let t = BOUNCE_START + FALL;
  events.push({ t, v: 1, i: 0, kind: "bounce" });
  let dur = 2 * FALL * BOUNCE_E;
  let h = DROP_M / 2;
  for (let k = 1; dur > 0.035; k++) {
    segs.push({ t0: t, dur, h, apex: true });
    t += dur;
    events.push({ t, v: BOUNCE_E ** k, i: k, kind: "bounce" });
    dur *= BOUNCE_E;
    h /= 2;
  }
  return { segs, events, restAt: t };
};

export const bounceHeight = (sim: ReturnType<typeof bounceSim>, t: number) => {
  if (t < BOUNCE_START) return DROP_M;
  if (t < BOUNCE_START + FALL) {
    const u = t - BOUNCE_START;
    return DROP_M - 0.5 * MOON_G * u * u;
  }
  const s = sim.segs.find((q) => t < q.t0 + q.dur);
  if (!s) return 0;
  const u = (t - s.t0) / s.dur;
  return 4 * s.h * u * (1 - u);
};
