import React from "react";
import { useCurrentFrame } from "remotion";
import { Caption, Ctx, Scene, background, fontFamily, glow, hexA, ripple, sphere } from "./kit";
import { FPS, H, W, smooth } from "./sims";
import {
  ACC,
  BODE,
  BOUNCE_START,
  DROP_M,
  LAPLACE_T0,
  MOONS,
  ROCK_COUNT,
  accretionSim,
  asteroidEvents,
  bodeAngle,
  bodeEvents,
  bodeHit,
  bodeState,
  bounceHeight,
  bounceSim,
  laplaceEvents,
  moonAngle,
  rockDust,
  rockHit,
  rockX,
} from "./sims-solar";

const FADE = (c: Ctx, t: number, color: string) => {
  const a = Math.max(1 - smooth(0, 0.5, t), smooth(19.5, 20, t));
  if (a > 0) {
    c.fillStyle = hexA(color, a);
    c.fillRect(0, 0, W, H);
  }
};

const starfield = Array.from({ length: 170 }, (_, i) => {
  const a = Math.sin(i * 127.1) * 43758.5453;
  const b = Math.sin(i * 311.7) * 43758.5453;
  const d = Math.sin(i * 74.7) * 43758.5453;
  return { x: (a - Math.floor(a)) * W, y: (b - Math.floor(b)) * H, s: d - Math.floor(d) };
});

const stars = (c: Ctx, t: number, limitY = H) => {
  for (const [i, s] of starfield.entries()) {
    if (s.y > limitY) continue;
    c.fillStyle = `rgba(235,240,255,${0.16 + 0.34 * s.s * (0.8 + 0.2 * Math.sin(t * 1.2 + i))})`;
    c.beginPath();
    c.arc(s.x, s.y, 0.8 + 1.3 * s.s, 0, Math.PI * 2);
    c.fill();
  }
};

const shade = (hex: string, f: number) => {
  const n = parseInt(hex.slice(1), 16);
  const m = (v: number) => Math.round(f > 1 ? v + (255 - v) * (f - 1) : v * f);
  return `rgb(${m(n >> 16)},${m((n >> 8) & 255)},${m(n & 255)})`;
};
const ball = (c: Ctx, x: number, y: number, r: number, hex: string) =>
  sphere(c, x, y, r, shade(hex, 1.65), hex, shade(hex, 0.32));

// ---------- 1. Doubling orbits ----------
const bodeEv = bodeEvents();
const CX = 540;
const CY = 930;

const drawBode = (c: Ctx, t: number) => {
  background(c, "#0B1026", "#05060F", "rgba(70,80,160,0.14)", CY);
  stars(c, t);
  const st = bodeState(t);
  const s = 390 / st.R;

  // Old orbits collapse towards the Sun as the camera backs away.
  for (const [i, p] of BODE.entries()) {
    const r = p.real * s;
    if (r > 1500) continue;
    const reached = t >= bodeHit(i);
    c.strokeStyle = `rgba(215,225,255,${reached ? 0.5 : 0.14})`;
    c.lineWidth = reached ? 2 : 1.4;
    c.beginPath();
    c.arc(CX, CY, r, 0, Math.PI * 2);
    c.stroke();
  }
  const sunR = Math.max(5, Math.min(70, 0.16 * s));
  glow(c, CX, CY, sunR * 2.6 + 26, "#FFCF80", 0.5);
  ball(c, CX, CY, sunR, "#FFC766");

  // Neptune's miss: the predicted ring appears beyond where Neptune really sits.
  const missing = smooth(bodeHit(8) + 0.2, bodeHit(8) + 1.2, t);
  if (missing > 0) {
    c.save();
    c.setLineDash([10, 12]);
    c.strokeStyle = `rgba(255,190,150,${0.75 * missing})`;
    c.lineWidth = 2.5;
    c.beginPath();
    c.arc(CX, CY, 38.8 * s, 0, Math.PI * 2);
    c.stroke();
    c.restore();
  }

  for (const [i, p] of BODE.entries()) {
    const a = bodeAngle(i);
    const age = t - bodeHit(i);
    const push = age >= 0 ? 16 * Math.exp(-age * 4.5) * Math.sin(Math.min(age * 16, Math.PI)) : 0;
    const dist = p.real * s + push;
    const x = CX + Math.cos(a) * dist;
    const y = CY + Math.sin(a) * dist;
    if (x < -150 || x > W + 150 || y < -150 || y > H + 150) continue;
    const scale = Math.min(1, Math.max(0.16, (p.real * s) / 260));
    const r = p.r * scale;
    if (age >= 0) ripple(c, x, y, age, p.c, 240, 1.5);
    glow(c, x, y, r * 3, p.c, age >= 0 && age < 1.5 ? 0.6 * (1 - age / 1.5) : 0.08);
    if (p.name === "Saturn") {
      c.strokeStyle = hexA(p.c, 0.65);
      c.lineWidth = Math.max(1, r * 0.18);
      c.beginPath();
      c.ellipse(x, y, r * 1.8, r * 0.5, -0.35, 0, Math.PI * 2);
      c.stroke();
    }
    ball(c, x, y, r, p.c);
  }

  const cx = CX + st.x * s;
  const cy = CY + st.y * s;
  for (let k = 12; k >= 1; k--) {
    const q = bodeState(t - k * 0.024);
    const sx = CX + q.x * s;
    const sy = CY + q.y * s;
    c.fillStyle = `rgba(190,240,255,${0.09 * (1 - k / 13)})`;
    c.beginPath();
    c.arc(sx, sy, 11 - k * 0.5, 0, Math.PI * 2);
    c.fill();
  }
  glow(c, cx, cy, 44, "#BDF2FF", 0.55);
  ball(c, cx, cy, 11, "#D8F6FF");
  FADE(c, t, "#070A1A");
};

const BodeLabel = () => {
  const t = useCurrentFrame() / FPS;
  const i = BODE.findLastIndex((_, k) => t >= bodeHit(k) - 0.05);
  if (i < 0) return null;
  const p = BODE[i];
  const age = t - bodeHit(i);
  const op = smooth(-0.05, 0.25, age);
  return (
    <div style={{ position: "absolute", top: 1450, left: 0, right: 0, textAlign: "center", fontFamily, fontWeight: 300, color: "#E8ECFF", opacity: op }}>
      <div style={{ fontSize: 68, color: p.c }}>{p.name}</div>
      <div style={{ fontSize: 40, opacity: 0.78, marginTop: 8 }}>
        predicted {p.pred} · real {p.real} AU
      </div>
    </div>
  );
};

export const BodeOrbits = () => (
  <Scene draw={drawBode} audio="bode">
    <Caption text="Each gap between worlds nearly doubles." from={0.3} to={bodeHit(8) - 0.1} color="#E8ECFF" y={220} size={58} />
    <Caption text="Until Neptune breaks the pattern." from={bodeHit(8) + 0.1} to={20} color="#FFD3B8" y={220} size={58} />
    <BodeLabel />
  </Scene>
);

// ---------- 2. Laplace resonance ----------
const lapEv = laplaceEvents();
const LX = 540;
const LY = 840;

const drawLaplace = (c: Ctx, t: number) => {
  background(c, "#17120F", "#07060A", "rgba(190,120,70,0.13)", LY);
  stars(c, t);

  // Jupiter with soft cloud bands.
  glow(c, LX, LY, 240, "#E8B88A", 0.2);
  c.save();
  c.beginPath();
  c.arc(LX, LY, 106, 0, Math.PI * 2);
  c.clip();
  ball(c, LX, LY, 106, "#D7A97F");
  [[-58, 12, 0.28], [-24, 20, 0.34], [18, 14, 0.3], [52, 18, 0.26]].forEach(([dy, h, a]) => {
    c.fillStyle = `rgba(120,70,45,${a})`;
    c.fillRect(LX - 110, LY + dy, 220, h);
  });
  c.restore();

  MOONS.forEach((m, i) => {
    c.strokeStyle = hexA(m.c, 0.34);
    c.lineWidth = 2;
    c.beginPath();
    c.arc(LX, LY, m.ring, 0, Math.PI * 2);
    c.stroke();
    // Each moon flicks a springy pin at the top of its own orbit.
    const last = lapEv.filter((e) => e.i === i && e.t <= t).at(-1);
    const age = last ? t - last.t : 9;
    const bend = 26 * Math.exp(-age * 4.2) * Math.sin(age * 22);
    const top = LY - m.ring;
    c.strokeStyle = hexA(m.c, 0.5 + 0.5 * Math.exp(-age * 3));
    c.lineWidth = 5;
    c.lineCap = "round";
    c.beginPath();
    c.moveTo(LX, top - 42);
    c.quadraticCurveTo(LX + bend * 0.35, top - 18, LX + bend, top + 4);
    c.stroke();
    if (age < 1.4) {
      ripple(c, LX, top, age, m.c, 180, 1.4);
      glow(c, LX, top, 110, m.c, 0.5 * Math.exp(-age * 4));
    }
    for (let k = 10; k >= 1; k--) {
      const a = ((moonAngle(m, t - k * 0.02) - 90) * Math.PI) / 180;
      c.fillStyle = hexA(m.c, 0.08 * (1 - k / 11));
      c.beginPath();
      c.arc(LX + Math.cos(a) * m.ring, LY + Math.sin(a) * m.ring, m.r, 0, Math.PI * 2);
      c.fill();
    }
    const a = ((moonAngle(m, t) - 90) * Math.PI) / 180;
    ball(c, LX + Math.cos(a) * m.ring, LY + Math.sin(a) * m.ring, m.r, m.c);
  });

  // The rhythm as a score: each row fills with dots at 4 : 2 : 1.
  const left = 250;
  const right = 960;
  MOONS.forEach((m, i) => {
    const y = 1385 + i * 56;
    c.strokeStyle = hexA(m.c, 0.22);
    c.lineWidth = 2;
    c.beginPath();
    c.moveTo(left, y);
    c.lineTo(right, y);
    c.stroke();
    c.fillStyle = hexA(m.c, 0.9);
    c.font = `300 34px ${fontFamily}`;
    c.textAlign = "right";
    c.textBaseline = "middle";
    c.fillText(m.name, left - 22, y);
    for (const e of lapEv) {
      if (e.i !== i || e.t > t) continue;
      const x = left + (e.t / 20) * (right - left);
      const pop = 1 + 0.9 * Math.exp(-(t - e.t) * 7);
      c.fillStyle = m.c;
      c.beginPath();
      c.arc(x, y, 9 * pop, 0, Math.PI * 2);
      c.fill();
    }
  });
  FADE(c, t, "#0D0A0A");
};

export const LaplaceRhythm = () => (
  <Scene draw={drawLaplace} audio="laplace">
    <Caption text="Jupiter's moons: a 4 : 2 : 1 rhythm." from={Math.min(0.3, LAPLACE_T0)} to={20} color="#F2E6D8" y={230} size={52} />
  </Scene>
);

// ---------- 3. Doubling asteroids ----------
const rockEv = asteroidEvents();
const dust = Array.from({ length: ROCK_COUNT }, (_, k) => rockDust(k));
const GROUND_Y = 1190;

const camState = (t: number) => {
  let lvl = 0;
  for (let k = 0; k < ROCK_COUNT - 1; k++) lvl += smooth(rockHit(k) + 0.55, rockHit(k) + 1.7, t);
  const low = Math.floor(lvl);
  const u = lvl - low;
  const x = rockX(low) + (rockX(Math.min(ROCK_COUNT - 1, low + 1)) - rockX(low)) * u;
  return { s: 240 / 2 ** lvl, x };
};

const drawAsteroids = (c: Ctx, t: number) => {
  background(c, "#090A12", "#050509", "rgba(90,95,130,0.07)", 700);
  stars(c, t, GROUND_Y);
  const { s, x: camX } = camState(t);
  const sx = (x: number) => 540 + (x - camX) * s;
  const sy = (y: number) => GROUND_Y - y * s;

  const g = c.createLinearGradient(0, GROUND_Y, 0, H);
  g.addColorStop(0, "#8D8B88");
  g.addColorStop(0.2, "#55534F");
  g.addColorStop(1, "#1E1D1C");
  c.fillStyle = g;
  c.fillRect(0, GROUND_Y, W, H - GROUND_Y);

  for (let k = 0; k < ROCK_COUNT; k++) {
    const age = t - rockHit(k);
    if (age < 0) continue;
    const grow = 1 - Math.exp(-age * 11);
    const D = 2 ** k * 1.1 * s * grow;
    const x = sx(rockX(k));
    if (D < 1.2 || x + D < -30 || x - D > W + 30) continue;
    c.fillStyle = "#A9A6A0";
    c.beginPath();
    c.ellipse(x, GROUND_Y + D * 0.11, D * 0.72, D * 0.2, 0, 0, Math.PI * 2);
    c.fill();
    const cg = c.createLinearGradient(0, GROUND_Y, 0, GROUND_Y + D * 0.28);
    cg.addColorStop(0, "#26252A");
    cg.addColorStop(1, "#5C5A57");
    c.fillStyle = cg;
    c.beginPath();
    c.ellipse(x, GROUND_Y + D * 0.12, D * 0.57, D * 0.14, 0, 0, Math.PI * 2);
    c.fill();
  }

  for (let k = 0; k < ROCK_COUNT; k++) {
    const age = t - rockHit(k);
    const size = 2 ** k;
    if (age >= -1.1 && age < 0) {
      const u = 1 + age / 1.1;
      const e = u * u;
      const wx = rockX(k) + size * 1.2 * (1 - e) * (k % 2 ? 1 : -1);
      const wy = size * 0.5 + size * 3.4 * (1 - e);
      const x = sx(wx);
      const y = sy(wy);
      const r = (size / 2) * s;
      c.save();
      c.strokeStyle = "rgba(255,226,190,0.2)";
      c.lineWidth = r * 0.8;
      c.lineCap = "round";
      c.beginPath();
      c.moveTo(x, y);
      c.lineTo(x + (k % 2 ? 1 : -1) * r * 2.2, y - r * 5.2);
      c.stroke();
      c.restore();
      sphere(c, x, y, r, "#D6CDBF", "#857C70", "#2A2622");
    }
    if (age >= 0 && age < 2.2) {
      for (const d of dust[k]) {
        const px = sx(rockX(k) + d.vx * size * age);
        const py = sy(size * (d.vy * age - 0.9 * age * age));
        if (py > GROUND_Y) continue;
        c.fillStyle = `rgba(226,218,204,${0.6 * (1 - age / 2.2)})`;
        c.beginPath();
        c.arc(px, py, Math.max(1, d.size * size * s), 0, Math.PI * 2);
        c.fill();
      }
      glow(c, sx(rockX(k)), GROUND_Y, 280, "#FFD9A8", 0.42 * Math.exp(-age * 4.5));
    }
  }
  FADE(c, t, "#08080D");
};

const AsteroidCounter = () => {
  const t = useCurrentFrame() / FPS;
  const k = Math.max(0, Math.min(ROCK_COUNT - 1, rockEv.filter((e) => e.t - 1.15 <= t).length - 1));
  const age = t - (rockHit(k) - 1.1);
  return (
    <div style={{ position: "absolute", top: 400, left: 0, right: 0, textAlign: "center", fontFamily, fontWeight: 300, color: "#F2EEE6", opacity: smooth(0.2, 0.8, t) * smooth(0, 0.3, age + 0.1) }}>
      <div style={{ fontSize: 112, lineHeight: 1, fontVariantNumeric: "tabular-nums" }}>{2 ** k} m wide</div>
      <div style={{ fontSize: 50, opacity: 0.74, marginTop: 20 }}>
        {(8 ** k).toLocaleString("en-US")}× the impact energy
      </div>
    </div>
  );
};

export const AsteroidDoubling = () => (
  <Scene draw={drawAsteroids} audio="asteroid">
    <Caption text="Twice as wide. Eight times the energy." from={0.3} to={20} color="#F2EEE6" y={230} size={47} />
    <AsteroidCounter />
  </Scene>
);

// ---------- 4. Accretion ----------
const acc = accretionSim();
const AX = 540;
const AY = 930;
const radiusOf = (m: number) => 14 * Math.cbrt(m);
const massHue = (m: number) => (m < 32 ? 30 - Math.log2(m) * 3 : 200);

const drawAccretion = (c: Ctx, t: number) => {
  background(c, "#0A1322", "#04060D", "rgba(255,180,90,0.11)", AY);
  stars(c, t);
  glow(c, AX, AY, 280, "#FFC476", 0.5);
  ball(c, AX, AY, 70, "#FFC766");

  const spin = t * 0.09;
  const at = (angle: number) => ({ x: AX + Math.cos(angle + spin) * ACC.ring, y: AY + Math.sin(angle + spin) * ACC.ring });
  const body = (angle: number, m: number, pop = 0) => {
    const p = at(angle);
    const r = radiusOf(m) * (1 + pop);
    const h = massHue(m);
    sphere(c, p.x, p.y, r, `hsl(${h},75%,84%)`, `hsl(${h},58%,60%)`, `hsl(${h},55%,22%)`);
  };

  const r = Math.min(ACC.rounds - 1, Math.max(0, Math.floor((t - ACC.start) / ACC.step)));
  for (const q of acc.rounds[r]) {
    if (t < q.start) {
      body(q.a, q.m);
      body(q.b, q.m);
    } else if (t < q.hit) {
      const u = (t - q.start) / (q.hit - q.start);
      const e = u * u * u;
      body(q.a + (q.mid - q.a) * e, q.m);
      body(q.b + (q.mid - q.b) * e, q.m);
    } else {
      const age = t - q.hit;
      body(q.mid, q.m * 2, 0.32 * Math.exp(-age * 7) * Math.cos(age * 18));
      const p = at(q.mid);
      if (age < 1.3) {
        ripple(c, p.x, p.y, age, "#FFE2BC", 110 + radiusOf(q.m * 2) * 3, 1.3);
        glow(c, p.x, p.y, 26 + radiusOf(q.m) * 3, "#FFD9A8", 0.4 * Math.exp(-age * 6));
      }
    }
  }
  FADE(c, t, "#070B15");
};

const AccCounter = () => {
  const t = useCurrentFrame() / FPS;
  const count = 64 - acc.events.filter((e) => e.t <= t).length;
  return (
    <div style={{ position: "absolute", top: 1420, left: 0, right: 0, textAlign: "center", fontFamily, fontWeight: 300, color: "#F2ECE0", opacity: smooth(0.2, 0.8, t), fontVariantNumeric: "tabular-nums" }}>
      <div style={{ fontSize: 150, lineHeight: 1 }}>{count}</div>
      <div style={{ fontSize: 42, opacity: 0.72, marginTop: 10 }}>{count === 1 ? "world" : "worlds"}</div>
    </div>
  );
};

export const Accretion = () => (
  <Scene draw={drawAccretion} audio="accretion">
    <Caption text="Planets grew by collision." from={0.3} to={20} color="#F2ECE0" y={230} />
    <AccCounter />
  </Scene>
);

// ---------- 5. Moon bounce ----------
const bounce = bounceSim();
const BG = 1370;

const bounceZoom = (t: number) => {
  // The camera follows the shrinking bounces, up to a limit.
  const blend = bounce.segs.reduce((sum, q) => sum + smooth(q.t0 - 0.4, q.t0 + q.dur * 0.2, t), 0);
  return 2 ** Math.min(blend, 5);
};

const drawBounce = (c: Ctx, t: number) => {
  background(c, "#05060C", "#02030A", "rgba(70,90,140,0.08)", 700);
  stars(c, t, BG);
  const z = bounceZoom(t);
  const pxPerM = (900 / DROP_M) * z;

  // Earth hangs in the lunar sky.
  ball(c, 880, 430, 52, "#6FA8DC");
  c.fillStyle = "rgba(2,3,10,0.62)";
  c.beginPath();
  c.arc(855, 419, 52, 0, Math.PI * 2);
  c.fill();

  const g = c.createLinearGradient(0, BG, 0, H);
  g.addColorStop(0, "#9B9994");
  g.addColorStop(0.3, "#5D5B57");
  g.addColorStop(1, "#1C1B1A");
  c.fillStyle = g;
  c.fillRect(0, BG, W, H - BG);

  // Height ladder: each mark is half the last, so the spacing is itself geometric.
  c.textAlign = "left";
  c.textBaseline = "middle";
  c.font = `300 34px ${fontFamily}`;
  for (let k = 0; k < 9; k++) {
    const m = DROP_M / 2 ** k;
    const y = BG - m * pxPerM;
    if (y < 120 || BG - y < 45) continue;
    const reached = bounce.segs[k - 1] ? t >= bounce.segs[k - 1].t0 + bounce.segs[k - 1].dur / 2 : k === 0;
    c.strokeStyle = `rgba(230,235,255,${reached ? 0.55 : 0.22})`;
    c.lineWidth = 2;
    c.beginPath();
    c.moveTo(70, y);
    c.lineTo(260, y);
    c.stroke();
    c.fillStyle = `rgba(230,235,255,${reached ? 0.9 : 0.42})`;
    c.fillText(m >= 1 ? `${m} m` : `${+(m * 100).toFixed(2)} cm`, 76, y - 24);
  }

  const R = 0.11 * pxPerM;
  const rNow = Math.min(120, R);
  const hNow = bounceHeight(bounce, t);
  const y = BG - hNow * pxPerM - rNow;
  const shadowA = 0.42 / (1 + hNow * pxPerM * 0.006);
  c.fillStyle = `rgba(0,0,0,${shadowA})`;
  c.beginPath();
  c.ellipse(600, BG + 10, rNow * 1.2, 9, 0, 0, Math.PI * 2);
  c.fill();
  for (const e of bounce.events) {
    const age = t - e.t;
    if (age < 0 || age > 1.5) continue;
    ripple(c, 600, BG, age, "#E6EEFF", 150 + 300 * (e.v as number), 1.5);
    glow(c, 600, BG, 170, "#DCE7FF", 0.5 * (e.v as number) * Math.exp(-age * 6));
  }
  ball(c, 600, y, rNow, "#D8DCE6");
  FADE(c, t, "#04050B");
};

const BounceCounter = () => {
  const t = useCurrentFrame() / FPS;
  const n = bounce.events.filter((e) => e.t <= t).length;
  return (
    <div style={{ position: "absolute", top: 1490, left: 0, right: 0, textAlign: "center", fontFamily, fontWeight: 300, color: "#111014", opacity: smooth(BOUNCE_START + 2, BOUNCE_START + 3, t) * (1 - smooth(bounce.restAt, bounce.restAt + 0.4, t)), fontSize: 56 }}>
      bounce {n}
    </div>
  );
};

export const MoonBounce = () => (
  <Scene draw={drawBounce} audio="bounce">
    <Caption text="On the Moon, each bounce reaches half the height." from={0.3} to={bounce.restAt - 0.3} color="#E8ECFF" y={190} size={54} />
    <Caption text="Endless bounces. Finite time." from={bounce.restAt - 0.1} to={20} color="#E8ECFF" y={520} size={72} />
    <BounceCounter />
  </Scene>
);
