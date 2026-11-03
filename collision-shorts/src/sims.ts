// Deterministic simulations shared by the renderer and the audio event export.
// No Remotion imports here, so scripts/export-events.ts can run it in plain Node.

export const FPS = 60;
export const DUR = 20;
export const FRAMES = FPS * DUR;
export const W = 1080;
export const H = 1920;

export type Ev = { t: number; v: number; i: number; kind: string; x?: number; y?: number };

const rng = (seed: number) => () => {
  seed = (seed + 0x6d2b79f5) | 0;
  let r = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
  return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
};

export const smooth = (a: number, b: number, x: number) => {
  const u = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return u * u * (3 - 2 * u);
};

// ---------- 1. Newton's cradle ----------
export const CRADLE = {
  phases: [
    { n: 1, t0: 0.2, end: 6.6 },
    { n: 2, t0: 6.6, end: 13.2 },
    { n: 3, t0: 13.2, end: 20 },
  ],
  lift: 0.7,
  hold: 0.15,
  period: 1.5,
  a0: 0.42,
  decay: 0.09,
  fade: 0.7,
};

export const cradleTheta = (t: number) => {
  const { phases, lift, hold, period, a0, decay, fade } = CRADLE;
  const p = [...phases].reverse().find((q) => t >= q.t0);
  if (!p) return { theta: 0, n: 1 };
  const u = t - p.t0;
  if (u < lift) return { theta: -a0 * smooth(0, lift, u), n: p.n };
  if (u < lift + hold) return { theta: -a0, n: p.n };
  const r = u - lift - hold;
  const amp = a0 * Math.exp(-decay * r) * (1 - smooth(p.end - fade, p.end, t));
  return { theta: -amp * Math.cos((2 * Math.PI * r) / period), n: p.n };
};

export const cradleEvents = (): Ev[] => {
  const { phases, lift, hold, period, a0, decay, fade } = CRADLE;
  const out: Ev[] = [];
  for (const p of phases) {
    const start = p.t0 + lift + hold;
    for (let j = 0; ; j++) {
      const t = start + period / 4 + (j * period) / 2;
      if (t >= p.end) break;
      const amp = a0 * Math.exp(-decay * (t - start)) * (1 - smooth(p.end - fade, p.end, t));
      if (amp < 0.03) break;
      out.push({ t, v: amp / a0, i: p.n, kind: "click" });
    }
  }
  return out;
};

// ---------- 2. String art inside a ring ----------
export const RING = { cx: 540, cy: 960, R: 440, g: 2000 };

export const ringSim = () => {
  const { cx, cy, R, g } = RING;
  const rand = rng(11);
  const traj = new Float32Array(FRAMES * 3);
  const events: Ev[] = [];
  let x = 60,
    y = -220,
    vx = 1050,
    vy = 0,
    r = 22;
  const energy = 0.5 * (vx * vx + vy * vy) + g * -y;
  const sub = 20;
  const dt = 1 / (FPS * sub);
  for (let f = 0; f < FRAMES; f++) {
    traj[f * 3] = cx + x;
    traj[f * 3 + 1] = cy + y;
    traj[f * 3 + 2] = r;
    for (let s = 0; s < sub; s++) {
      vy += g * dt;
      x += vx * dt;
      y += vy * dt;
      const d = Math.hypot(x, y);
      if (d + r >= R) {
        const nx = x / d,
          ny = y / d;
        const dot = vx * nx + vy * ny;
        if (dot > 0) {
          const t = (f + s / sub) / FPS;
          vx -= 2 * dot * nx;
          vy -= 2 * dot * ny;
          x = nx * (R - r);
          y = ny * (R - r);
          // A tiny tangential nudge keeps the path from settling into a loop.
          const nudge = (rand() - 0.5) * 34;
          vx += -ny * nudge;
          vy += nx * nudge;
          // Never leave at a grazing angle, or the ball slides along the wall.
          const inward = -(vx * nx + vy * ny);
          if (inward < 420) {
            vx -= (420 - inward) * nx;
            vy -= (420 - inward) * ny;
          }
          const target = Math.sqrt(Math.max(1, 2 * (energy + g * y)));
          const sp = Math.hypot(vx, vy);
          vx *= target / sp;
          vy *= target / sp;
          events.push({
            t,
            v: Math.min(1, dot / 1100),
            i: events.length,
            kind: "bounce",
            x: cx + nx * R,
            y: cy + ny * R,
          });
          r = Math.min(250, r + 3.2);
        }
      }
    }
  }
  return { traj, events };
};

// ---------- 3. Pi from colliding blocks ----------
export const PI_SCENE = { wallX: 90, floorY: 1240, smallW: 40, d: 800, gap: 300, speed: 300 };

type PiSeg = { video: number; sim: number; x1: number; v1: number; x2: number; v2: number };

const piRun = (mass: number, vs: number, lead: number, ve: number, tailEnd: number) => {
  const { d, gap, speed } = PI_SCENE;
  let x1 = d,
    v1 = 0,
    x2 = d + gap,
    v2 = -speed,
    sim = 0;
  const raw: PiSeg[] = [{ video: vs, sim: 0, x1, v1, x2, v2 }];
  const hits: { sim: number; wall: boolean }[] = [];
  for (;;) {
    const tBlock = v1 > v2 ? (x2 - x1) / (v1 - v2) : Infinity;
    const tWall = v1 < 0 ? x1 / -v1 : Infinity;
    const dt = Math.min(tBlock, tWall);
    if (!Number.isFinite(dt)) break;
    x1 += v1 * dt;
    x2 += v2 * dt;
    sim += dt;
    if (tBlock <= tWall) {
      const a = ((1 - mass) * v1 + 2 * mass * v2) / (1 + mass);
      const b = (2 * v1 + (mass - 1) * v2) / (1 + mass);
      v1 = a;
      v2 = b;
      x1 = x2;
      hits.push({ sim, wall: false });
    } else {
      v1 = -v1;
      x1 = 0;
      hits.push({ sim, wall: true });
    }
    raw.push({ video: 0, sim, x1, v1, x2, v2 });
  }
  // Warp time: a blend of even spacing per hit and true time keeps dense bursts readable.
  const N = hits.length;
  const first = hits[0].sim;
  const last = hits[N - 1].sim;
  const alpha = 0.72;
  raw.forEach((seg, k) => {
    if (k === 0) return;
    const u = alpha * ((k - 1) / (N - 1)) + (1 - alpha) * ((seg.sim - first) / (last - first));
    seg.video = vs + lead + (ve - vs - lead) * u;
  });
  const lastSeg = raw[raw.length - 1];
  raw.push({ ...lastSeg, video: tailEnd, sim: lastSeg.sim + (tailEnd - ve), x1: lastSeg.x1 + lastSeg.v1 * (tailEnd - ve), x2: lastSeg.x2 + lastSeg.v2 * (tailEnd - ve) });
  const events: Ev[] = hits.map((h, k) => ({
    t: raw[k + 1].video,
    v: Math.min(1, Math.abs(raw[k + 1].v1) / (speed * 12)),
    i: k,
    kind: h.wall ? "wall" : "block",
  }));
  return { mass, segs: raw, events, vs, ve, tailEnd, count: N };
};

export const piSim = () => [piRun(100, 0, 1.0, 4.2, 6.5), piRun(10000, 6.5, 1.0, 16.2, 20)];

export const piState = (run: ReturnType<typeof piRun>, t: number) => {
  const { segs } = run;
  let lo = 0,
    hi = segs.length - 2;
  while (lo < hi) {
    const m = (lo + hi + 1) >> 1;
    if (segs[m].video <= t) lo = m;
    else hi = m - 1;
  }
  const a = segs[lo];
  const b = segs[lo + 1];
  const u = Math.max(0, Math.min(1, (t - a.video) / Math.max(1e-9, b.video - a.video)));
  const s = (b.sim - a.sim) * u;
  return { x1: a.x1 + a.v1 * s, x2: a.x2 + a.v2 * s };
};

// ---------- 4. Galton board ----------
export const GALTON = {
  rows: 10,
  sx: 72,
  sy: 62,
  top: 440,
  cx: 540,
  binTop: 1070,
  floor: 1600,
  count: 620,
  ballR: 7,
  pegR: 7,
  spawnEnd: 14,
};

export const pegXY = (row: number, j: number) => ({
  x: GALTON.cx + (j - row / 2) * GALTON.sx,
  y: GALTON.top + row * GALTON.sy,
});

export const galtonSim = () => {
  const { rows, sx, sy, top, cx, binTop, floor, count, ballR, pegR, spawnEnd } = GALTON;
  const rand = rng(2024);
  const pos = new Float32Array(count * FRAMES * 2).fill(NaN);
  const bins = new Int16Array(count).fill(5);
  const fill = new Array(rows + 1).fill(0);
  const events: Ev[] = [];
  const hitsByFrame: { row: number; j: number }[][] = Array.from({ length: FRAMES }, () => []);
  const balls = Array.from({ length: count }, (_, i) => ({
    x: cx + (rand() - 0.5) * 5,
    y: top - 110,
    vx: 0,
    vy: 40,
    born: 0.3 + (i / count) * (spawnEnd - 0.3),
    state: 0, // 0 falling through pegs, 1 in a channel, 2 at rest
    slotX: 0,
    slotY: 0,
    cool: 0,
  }));
  const sub = 5;
  const dt = 1 / (FPS * sub);
  const g = 1700;
  const minD = ballR + pegR;
  for (let f = 0; f < FRAMES; f++) {
    const now = f / FPS;
    for (let b = 0; b < count; b++) {
      const q = balls[b];
      if (now < q.born) continue;
      if (q.state < 2) {
        for (let s = 0; s < sub; s++) {
          q.vy += g * dt;
          q.x += q.vx * dt;
          q.y += q.vy * dt;
          q.vx *= 0.9985;
          if (q.state === 0) {
            const rowF = (q.y - top) / sy;
            for (const row of [Math.floor(rowF), Math.ceil(rowF)]) {
              if (row < 0 || row >= rows) continue;
              const j = Math.round((q.x - cx) / sx + row / 2);
              if (j < 0 || j > row) continue;
              const pg = pegXY(row, j);
              const dx = q.x - pg.x,
                dy = q.y - pg.y;
              const d = Math.hypot(dx, dy);
              if (d < minD && d > 0) {
                const nx = dx / d,
                  ny = dy / d;
                const dot = q.vx * nx + q.vy * ny;
                if (dot < 0) {
                  // A fair left/right hop that lands on a peg of the next row, so the
                  // result is truly binomial and the bell curve is earned, not faked.
                  const up = 40 + rand() * 50;
                  const T = (up + Math.sqrt(up * up + 2 * g * sy)) / g;
                  q.vx = ((rand() < 0.5 ? -1 : 1) * (sx / 2)) / T;
                  q.vy = -up;
                  q.x = pg.x;
                  q.y = pg.y - minD;
                  if (now - q.cool > 0.05) {
                    q.cool = now;
                    hitsByFrame[f].push({ row, j });
                    events.push({ t: now, v: Math.min(1, -dot / 700), i: row, kind: "peg", x: pg.x });
                  }
                }
              }
            }
            const rail = 36 * Math.max(0, (q.y - top) / sy) + 40;
            if (Math.abs(q.x - cx) > rail) {
              q.x = cx + Math.sign(q.x - cx) * rail;
              q.vx *= -0.4;
            }
            if (q.y >= binTop - 30) {
              const bin = Math.max(0, Math.min(rows, Math.round((q.x - cx) / sx + rows / 2)));
              bins[b] = bin;
              const n = fill[bin]++;
              const col = n % 5;
              const row = Math.floor(n / 5);
              q.slotX = cx + (bin - rows / 2) * sx + (col - 2) * 13.4 + (row % 2) * 3;
              q.slotY = floor - ballR - row * 12.5;
              q.state = 1;
              q.vx = 0;
              q.vy = Math.min(q.vy, 520);
            }
          } else {
            q.x += (q.slotX - q.x) * 0.05;
            if (q.y >= q.slotY) {
              q.x = q.slotX;
              q.y = q.slotY;
              q.state = 2;
              events.push({ t: now, v: Math.min(1, q.vy / 900), i: bins[b], kind: "land", x: q.x });
              break;
            }
          }
        }
      }
      pos[(b * FRAMES + f) * 2] = q.x;
      pos[(b * FRAMES + f) * 2 + 1] = q.y;
    }
  }
  events.sort((a, b) => a.t - b.t);
  return { pos, bins, fill, events, hitsByFrame };
};

// ---------- 5. Ball-played xylophone ----------
const BEAT = 0.588;
const START = 0.67;
export const XYLO = { beat: BEAT, start: START, topY: 980, bassY: 1400, ballR: 26, bassR: 34, g: 3000, gBass: 1400 };

const MELODY: [number, number][] = [
  [0, 1], [2, 1], [3, 1], [5, 1], [4, 1.5], [3, 0.5], [2, 1], [3, 1],
  [1, 1], [3, 1], [4, 1], [6, 1], [5, 1.5], [4, 0.5], [3, 2],
  [5, 1], [6, 0.5], [7, 0.5], [6, 1], [5, 1], [3, 1], [4, 1], [2, 2],
  [0, 1], [2, 1], [3, 1], [1, 1], [0, 0],
];
const BASS = [3, 2, 0, 1, 3, 2, 0, 1, 3, 1, 3];

export const topBarX = (i: number) => 162 + i * 108;
export const bassBarX = (i: number) => 180 + i * 180;

export type Arc = { t0: number; t1: number; x0: number; x1: number; y0: number; y1: number; g: number };

const arc = (t0: number, t1: number, x0: number, x1: number, y0: number, y1: number, g: number): Arc => ({ t0, t1, x0, x1, y0, y1, g });

export const arcPos = (arcs: Arc[], t: number) => {
  const a = arcs.find((q) => t < q.t1) ?? arcs[arcs.length - 1];
  const u = Math.max(0, Math.min(a.t1 - a.t0, t - a.t0));
  const T = a.t1 - a.t0;
  const vy = (a.y1 - a.y0) / T - 0.5 * a.g * T;
  return { x: a.x0 + ((a.x1 - a.x0) * u) / T, y: a.y0 + vy * u + 0.5 * a.g * u * u };
};

export const xyloSim = () => {
  const { topY, bassY, ballR, bassR, g, gBass } = XYLO;
  const events: Ev[] = [];
  const arcs: Arc[] = [];
  const rest = topY - ballR;
  let t = START;
  arcs.push(arc(0, START, topBarX(MELODY[0][0]), topBarX(MELODY[0][0]), rest - 0.5 * g * START * START, rest, g));
  MELODY.forEach(([n, beats], k) => {
    events.push({ t, v: 0.72 + 0.28 * (beats >= 1.5 ? 1 : beats >= 1 ? 0.6 : 0.2), i: n, kind: "top" });
    const next = MELODY[k + 1];
    if (next) {
      const t1 = t + beats * BEAT;
      arcs.push(arc(t, t1, topBarX(n), topBarX(next[0]), rest, rest, g));
      t = t1;
    }
  });
  // Settling bounces on the last bar.
  const lastX = topBarX(MELODY[MELODY.length - 1][0]);
  [0.42, 0.26, 0.15, 0.08].forEach((dt, k) => {
    arcs.push(arc(t, t + dt, lastX, lastX, rest, rest, g));
    t += dt;
    events.push({ t, v: 0.3 - k * 0.06, i: MELODY[MELODY.length - 1][0], kind: "top" });
  });
  arcs.push(arc(t, 30, lastX, lastX, rest, rest, 0));

  const bassArcs: Arc[] = [];
  const bRest = bassY - bassR;
  let bt = START + 8 * BEAT;
  bassArcs.push(arc(bt - 2 * BEAT, bt, -60, bassBarX(BASS[0]), bRest - 60, bRest, gBass));
  BASS.forEach((n, k) => {
    events.push({ t: bt, v: 0.8, i: n, kind: "bass" });
    const next = BASS[k + 1];
    if (next !== undefined) {
      bassArcs.push(arc(bt, bt + 2 * BEAT, bassBarX(n), bassBarX(next), bRest, bRest, gBass));
      bt += 2 * BEAT;
    }
  });
  const bLast = bassBarX(BASS[BASS.length - 1]);
  [0.5, 0.3, 0.16].forEach((dt, k) => {
    bassArcs.push(arc(bt, bt + dt, bLast, bLast, bRest, bRest, gBass));
    bt += dt;
    events.push({ t: bt, v: 0.3 - k * 0.08, i: BASS[BASS.length - 1], kind: "bass" });
  });
  bassArcs.push(arc(bt, 30, bLast, bLast, bRest, bRest, 0));
  events.sort((a, b) => a.t - b.t);
  return { arcs, bassArcs, events, bassStart: START + 6 * BEAT };
};
