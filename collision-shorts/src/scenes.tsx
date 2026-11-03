import React from "react";
import { useCurrentFrame } from "remotion";
import { Caption, Ctx, Scene, background, fontFamily, glow, hexA, ripple, sphere } from "./kit";
import {
  CRADLE,
  FPS,
  GALTON,
  H,
  PI_SCENE,
  RING,
  W,
  XYLO,
  arcPos,
  bassBarX,
  cradleEvents,
  cradleTheta,
  galtonSim,
  pegXY,
  piSim,
  piState,
  ringSim,
  smooth,
  topBarX,
  xyloSim,
} from "./sims";

const FADE = (c: Ctx, t: number, color: string) => {
  const a = Math.max(1 - smooth(0, 0.5, t), smooth(19.5, 20, t));
  if (a > 0) {
    c.fillStyle = hexA(color, a);
    c.fillRect(0, 0, W, H);
  }
};

// ---------- 1. Newton's cradle ----------
const CR = { rodY: 560, L: 560, r: 55, gap: 110, floor: 1250 };
const crEvents = cradleEvents();

const cradlePos = (i: number, t: number) => {
  const { theta, n } = cradleTheta(t);
  const moving = (theta < 0 && i < n) || (theta > 0 && i >= 5 - n);
  const a = moving ? theta : 0;
  const px = 540 + (i - 2) * CR.gap;
  return { px, x: px + CR.L * Math.sin(a), y: CR.rodY + CR.L * Math.cos(a), moving };
};

const drawCradle = (c: Ctx, t: number) => {
  background(c, "#F1ECE2", "#D8D1C4", "rgba(255,250,240,0.9)", 900);
  const ink = "#3A3631";
  // Floor shadow first, then the frame.
  for (let i = 0; i < 5; i++) {
    const p = cradlePos(i, t);
    const lift = (CR.rodY + CR.L - p.y) / 120;
    c.fillStyle = hexA("#4A4238", 0.2 / (1 + lift * 1.4));
    c.beginPath();
    c.ellipse(p.x, CR.floor + 16, CR.r * (1 + lift * 0.3), 15, 0, 0, Math.PI * 2);
    c.fill();
  }
  c.strokeStyle = hexA(ink, 0.8);
  c.lineCap = "round";
  c.lineWidth = 7;
  c.beginPath();
  c.moveTo(-20, CR.rodY);
  c.lineTo(W + 20, CR.rodY);
  c.stroke();
  c.lineWidth = 5;
  c.strokeStyle = hexA(ink, 0.35);
  c.beginPath();
  c.moveTo(-20, CR.floor + 14);
  c.lineTo(W + 20, CR.floor + 14);
  c.stroke();

  const accent = ["#C9694A", "#E9A488", "#7E3A26"] as const;
  const steel = ["#F4F1EC", "#7E7A74", "#2B2926"] as const;
  // Soft motion echoes of the swinging balls.
  for (let k = 7; k >= 1; k--) {
    for (let i = 0; i < 5; i++) {
      const p = cradlePos(i, t - k * 0.022);
      if (!p.moving) continue;
      c.fillStyle = hexA("#C9694A", 0.05 * (1 - k / 8));
      c.beginPath();
      c.arc(p.x, p.y, CR.r, 0, Math.PI * 2);
      c.fill();
    }
  }
  for (let i = 0; i < 5; i++) {
    const p = cradlePos(i, t);
    c.strokeStyle = hexA(ink, 0.55);
    c.lineWidth = 2.5;
    c.beginPath();
    c.moveTo(p.px, CR.rodY);
    c.lineTo(p.x, p.y);
    c.stroke();
    if (p.moving) sphere(c, p.x, p.y, CR.r, "#F7D9CB", accent[0], accent[2]);
    else sphere(c, p.x, p.y, CR.r, steel[0], steel[1], steel[2]);
  }
  // Each strike sends a soft ring out from the contact point.
  for (const e of crEvents) {
    const age = t - e.t;
    if (age < 0 || age > 1.1) continue;
    const y = CR.rodY + CR.L;
    glow(c, 540, y, 320 * e.v + 60, "#FFF2DF", 0.42 * e.v * Math.exp(-age * 7), "screen");
    ripple(c, 540, y, age, "#B5593C", 460, 1.1);
  }
  FADE(c, t, "#F1ECE2");
};

export const Cradle = () => {
  const ink = "#3A3631";
  const [a, b, d] = CRADLE.phases;
  return (
    <Scene draw={drawCradle} audio="cradle">
      <Caption text="Nothing is lost." from={0.3} to={20} color={ink} y={320} />
      <Caption text="one in, one out" from={a.t0 + 0.5} to={a.end} color={hexA(ink, 0.65)} y={1370} size={46} />
      <Caption text="two in, two out" from={b.t0 + 0.5} to={b.end} color={hexA(ink, 0.65)} y={1370} size={46} />
      <Caption text="three in, three out" from={d.t0 + 0.5} to={19.8} color={hexA(ink, 0.65)} y={1370} size={46} />
    </Scene>
  );
};

// ---------- 2. Ring string art ----------
const ring = ringSim();

const drawRing = (c: Ctx, t: number, f: number) => {
  background(c, "#10163A", "#070A1F", "rgba(70,90,190,0.28)");
  const { cx, cy, R } = RING;
  const hitsNow = ring.events.filter((e) => e.t <= t);
  const hue = (k: number) => 195 + (k / ring.events.length) * 135;

  c.save();
  c.globalCompositeOperation = "lighter";
  c.lineWidth = 1.6;
  for (let k = 1; k < hitsNow.length; k++) {
    const a = hitsNow[k - 1];
    const b = hitsNow[k];
    const age = t - b.t;
    c.strokeStyle = `hsla(${hue(k)},85%,70%,${0.26 + 0.6 * Math.exp(-age * 3)})`;
    c.beginPath();
    c.moveTo(a.x!, a.y!);
    c.lineTo(b.x!, b.y!);
    c.stroke();
  }
  c.restore();

  c.strokeStyle = "rgba(225,232,255,0.75)";
  c.lineWidth = 4;
  c.beginPath();
  c.arc(cx, cy, R, 0, Math.PI * 2);
  c.stroke();

  for (const e of hitsNow.slice(-24)) {
    const age = t - e.t;
    const col = `hsl(${hue(e.i)},90%,76%)`;
    c.fillStyle = col;
    c.beginPath();
    c.arc(e.x!, e.y!, 5, 0, Math.PI * 2);
    c.fill();
    if (age < 0.8) {
      c.strokeStyle = `hsla(${hue(e.i)},90%,76%,${0.6 * (1 - age / 0.8) ** 2})`;
      c.lineWidth = 2.5;
      c.beginPath();
      c.arc(e.x!, e.y!, 6 + 120 * (1 - (1 - age / 0.8) ** 2), 0, Math.PI * 2);
      c.stroke();
    }
  }

  const k = hitsNow.length;
  const h = hue(k);
  for (let b = 14; b >= 1; b--) {
    const g = Math.max(0, f - b * 2) * 3;
    c.fillStyle = `hsla(${h},80%,70%,${0.05 * (1 - b / 15)})`;
    c.beginPath();
    c.arc(ring.traj[g], ring.traj[g + 1], ring.traj[g + 2], 0, Math.PI * 2);
    c.fill();
  }
  const x = ring.traj[f * 3];
  const y = ring.traj[f * 3 + 1];
  const r = ring.traj[f * 3 + 2];
  sphere(c, x, y, r, `hsl(${h},95%,92%)`, `hsl(${h},75%,66%)`, `hsl(${h},70%,32%)`);
  FADE(c, t, "#0A0E28");
};

export const RingArt = () => (
  <Scene draw={drawRing} audio="ring">
    <Caption text="Every bounce leaves a line." from={0.3} to={20} color="#E6EAFF" y={240} />
  </Scene>
);

// ---------- 3. Pi blocks ----------
const pi = piSim();
const PI_INK = "#22332F";
const bigSize = [130, 190];

const block = (c: Ctx, x: number, floor: number, w: number, h: number, top: string, bottom: string) => {
  const g = c.createLinearGradient(0, floor - h, 0, floor);
  g.addColorStop(0, top);
  g.addColorStop(1, bottom);
  c.fillStyle = g;
  c.beginPath();
  c.roundRect(x, floor - h, w, h, Math.min(10, w * 0.1));
  c.fill();
};

const drawPi = (c: Ctx, t: number) => {
  background(c, "#E6EBE1", "#C6D2C7", "rgba(255,255,248,0.75)", 1100);
  const { wallX, floorY, smallW } = PI_SCENE;
  const idx = t < 6.5 ? 0 : 1;
  const run = pi[idx];
  const { x1, x2 } = piState(run, t);
  const fadeIn = smooth(run.vs, run.vs + 0.5, t);
  const zoomT = idx === 1 ? Math.min(4, 700 / (x2 + 40)) : 1;
  const zoom = Math.max(1, zoomT);

  c.save();
  c.translate(wallX, floorY);
  c.scale(zoom, zoom);
  c.translate(-wallX, -floorY);
  c.fillStyle = hexA(PI_INK, 0.9);
  c.fillRect(wallX - 400, floorY, 2600, 5);
  c.fillRect(wallX - 8, floorY - 1600, 8, 1600);

  c.globalAlpha = fadeIn;
  const s = bigSize[idx];
  c.fillStyle = hexA(PI_INK, 0.14);
  c.beginPath();
  c.ellipse(wallX + x2 + s / 2, floorY + 8, s * 0.55, 6, 0, 0, Math.PI * 2);
  c.fill();
  block(c, wallX + x2 + smallW, floorY, s, s, "#3F645B", "#2A4840");
  block(c, wallX + x1, floorY, smallW, smallW, "#F6B27F", "#E2814D");
  c.fillStyle = "#F1F4EC";
  c.font = `300 ${s * 0.2}px ${fontFamily}`;
  c.textAlign = "center";
  c.textBaseline = "middle";
  c.fillText(`${run.mass.toLocaleString("en-US")}×`, wallX + x2 + smallW + s / 2, floorY - s / 2);
  c.globalAlpha = 1;

  // Contact flashes: subtle, so a dense burst shimmers instead of strobing.
  const latest = run.events.filter((e) => e.t <= t).at(-1);
  if (latest && t - latest.t < 0.22) {
    const st = piState(run, latest.t);
    const hx = latest.kind === "wall" ? wallX : wallX + st.x1 + smallW;
    glow(c, hx, floorY - smallW / 2, 34 / Math.sqrt(zoom) + 12, "#FFE3BD", 0.3 * (1 - (t - latest.t) / 0.22), "screen");
  }
  c.restore();
  FADE(c, t, "#E6EBE1");
};

const PiOverlay = () => {
  const t = useCurrentFrame() / FPS;
  const idx = t < 6.5 ? 0 : 1;
  const count = pi[idx].events.filter((e) => e.t <= t).length;
  const op = smooth(pi[idx].vs, pi[idx].vs + 0.5, t) * (idx === 0 ? 1 - smooth(6.05, 6.5, t) : 1);
  return (
    <div
      style={{
        position: "absolute",
        top: 215,
        left: 0,
        right: 0,
        textAlign: "center",
        fontFamily,
        fontWeight: 300,
        color: PI_INK,
        opacity: op,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      <div style={{ fontSize: 190, lineHeight: 1 }}>{count}</div>
      <div style={{ fontSize: 42, opacity: 0.7, marginTop: 6 }}>collisions</div>
    </div>
  );
};

export const PiBlocks = () => (
  <Scene draw={drawPi} audio="pi">
    <PiOverlay />
    <Caption text="π = 3.1…" from={4.4} to={6.3} color={PI_INK} y={1340} size={84} />
    <Caption text="π = 3.14…" from={16.4} to={20} color={PI_INK} y={1340} size={84} />
    <Caption text="Add two zeros to the mass, get the next digit." from={16.9} to={20} color={hexA(PI_INK, 0.7)} y={1460} size={40} />
  </Scene>
);

// ---------- 4. Galton board ----------
const galton = galtonSim();
const G_STOPS: [number, number, number][] = [
  [78, 196, 196],
  [244, 180, 90],
  [240, 110, 130],
];
const binColor = (b: number) => {
  const u = Math.abs(b - GALTON.rows / 2) / (GALTON.rows / 2);
  const s = u < 0.5 ? 0 : 1;
  const w = u < 0.5 ? u * 2 : (u - 0.5) * 2;
  const a = G_STOPS[2 - s];
  const d = G_STOPS[1 - s];
  return `rgb(${a.map((v, i) => Math.round(v + (d[i] - v) * w)).join(",")})`;
};
const binColors = Array.from({ length: GALTON.rows + 1 }, (_, i) => binColor(i));

const drawGalton = (c: Ctx, t: number, f: number) => {
  background(c, "#1B1128", "#0C0814", "rgba(120,70,150,0.22)", 800);
  const { rows, sx, cx, binTop, floor, count, ballR, top } = GALTON;

  // Funnel and channel dividers.
  c.strokeStyle = "rgba(235,225,250,0.3)";
  c.lineWidth = 3;
  c.lineCap = "round";
  c.beginPath();
  c.moveTo(cx - 90, top - 175);
  c.lineTo(cx - 18, top - 100);
  c.moveTo(cx + 90, top - 175);
  c.lineTo(cx + 18, top - 100);
  for (let b = 0; b <= rows + 1; b++) {
    const x = cx + (b - (rows + 1) / 2) * sx;
    c.moveTo(x, binTop);
    c.lineTo(x, floor);
  }
  c.moveTo(cx - ((rows + 1) * sx) / 2, floor);
  c.lineTo(cx + ((rows + 1) * sx) / 2, floor);
  c.stroke();

  // Pegs warm up when they are struck, then cool off.
  const heat = new Map<string, number>();
  for (let k = 0; k < 16 && f - k >= 0; k++) {
    for (const h of galton.hitsByFrame[f - k]) {
      const key = `${h.row}:${h.j}`;
      heat.set(key, Math.min(1, (heat.get(key) ?? 0) + 0.34 * (1 - k / 16)));
    }
  }
  for (let row = 0; row < rows; row++) {
    for (let j = 0; j <= row; j++) {
      const p = pegXY(row, j);
      const h = heat.get(`${row}:${j}`) ?? 0;
      glow(c, p.x, p.y, 14 + 18 * h, "#FFD7B0", 0.32 * h);
      c.fillStyle = `rgba(${235 + 20 * h},${225 + 5 * h},${250 - 80 * h},${0.55 + 0.45 * h})`;
      c.beginPath();
      c.arc(p.x, p.y, GALTON.pegR, 0, Math.PI * 2);
      c.fill();
    }
  }

  for (let b = 0; b < count; b++) {
    const i = (b * 1200 + f) * 2;
    const x = galton.pos[i];
    const y = galton.pos[i + 1];
    if (Number.isNaN(x)) continue;
    c.fillStyle = binColors[galton.bins[b]];
    c.beginPath();
    c.arc(x, y, ballR, 0, Math.PI * 2);
    c.fill();
    c.fillStyle = "rgba(255,255,255,0.42)";
    c.beginPath();
    c.arc(x - 2, y - 2.4, 2.1, 0, Math.PI * 2);
    c.fill();
  }

  // Once everything has landed, the curve the marbles made is traced over them.
  const draw = smooth(17.9, 19.2, t);
  if (draw > 0) {
    const peak = Math.max(...galton.fill);
    const curve = (b: number) => {
      const z = (b - rows / 2) / Math.sqrt(rows / 4);
      return floor - ((peak * 12.5) / 5 + 22) * Math.exp(-0.5 * z * z);
    };
    c.save();
    c.strokeStyle = "rgba(255,246,232,0.92)";
    c.lineWidth = 4;
    c.beginPath();
    const steps = 120;
    for (let s = 0; s <= steps * draw; s++) {
      const b = -0.5 + (s / steps) * (rows + 1);
      const x = cx + (b - rows / 2) * sx;
      if (s === 0) c.moveTo(x, curve(b));
      else c.lineTo(x, curve(b));
    }
    c.stroke();
    c.restore();
  }
  FADE(c, t, "#120B1C");
};

export const Galton = () => (
  <Scene draw={drawGalton} audio="galton">
    <Caption text="Chance has a shape." from={0.3} to={20} color="#EFE6F8" y={165} />
  </Scene>
);

// ---------- 5. Xylophone ----------
const xylo = xyloSim();
const barHue = (i: number) => 178 - i * 4;
const bassHue = (i: number) => 205 + i * 9;

const lastHit = (kind: string, i: number, t: number) => {
  let best = Infinity;
  for (const e of xylo.events) {
    if (e.kind === kind && e.i === i && e.t <= t) best = t - e.t;
  }
  return best;
};
const dip = (age: number, amp: number) => (age === Infinity ? 0 : amp * Math.exp(-age * 11) * Math.cos(age * 34));

const drawXylo = (c: Ctx, t: number) => {
  background(c, "#0A2230", "#050E16", "rgba(40,140,150,0.22)", 1100);
  const { topY, bassY, ballR, bassR } = XYLO;

  // Top row: pipes get shorter as the pitch rises.
  for (let i = 0; i < 8; i++) {
    const x = topBarX(i);
    const age = lastHit("top", i, t);
    const y = topY + dip(age, 16);
    const lit = age === Infinity ? 0 : Math.exp(-age * 2.6);
    const h = barHue(i);
    const len = 150 - i * 12;
    c.fillStyle = `hsla(${h},45%,${30 + 20 * lit}%,0.5)`;
    c.fillRect(x - 3, y + 14, 6, len);
    glow(c, x, y + 6, 70 + 120 * lit, `#7FE8D8`, 0.4 * lit);
    c.fillStyle = `hsl(${h},${58 + 30 * lit}%,${52 + 26 * lit}%)`;
    c.beginPath();
    c.roundRect(x - 47, y, 94, 18, 9);
    c.fill();
  }
  // Bass row fades in as the second ball arrives.
  const bassIn = smooth(xylo.bassStart - 0.4, xylo.bassStart + 0.5, t);
  c.globalAlpha = bassIn;
  for (let i = 0; i < 5; i++) {
    const x = bassBarX(i);
    const age = lastHit("bass", i, t);
    const y = bassY + dip(age, 20);
    const lit = age === Infinity ? 0 : Math.exp(-age * 1.9);
    const h = bassHue(i);
    c.fillStyle = `hsla(${h},40%,${28 + 20 * lit}%,0.5)`;
    c.fillRect(x - 4, y + 22, 8, 110 - i * 8);
    glow(c, x, y + 8, 100 + 150 * lit, "#89B8F0", 0.36 * lit);
    c.fillStyle = `hsl(${h},${50 + 30 * lit}%,${46 + 26 * lit}%)`;
    c.beginPath();
    c.roundRect(x - 78, y, 156, 24, 12);
    c.fill();
  }
  c.globalAlpha = 1;

  for (const e of xylo.events) {
    const age = t - e.t;
    if (age < 0 || age > 1.4) continue;
    const bass = e.kind === "bass";
    const x = bass ? bassBarX(e.i) : topBarX(e.i);
    const y = bass ? bassY : topY;
    ripple(c, x, y, age, bass ? "#9CC6F5" : "#9FF0E2", (bass ? 300 : 210) * e.v, 1.4);
  }

  const drawBall = (arcs: typeof xylo.arcs, r: number, a: string, b: string, d: string, trail: string, hit: string) => {
    for (let k = 12; k >= 1; k--) {
      const p = arcPos(arcs, t - k * 0.016);
      c.fillStyle = hexA(trail, 0.06 * (1 - k / 13));
      c.beginPath();
      c.arc(p.x, p.y, r * (1 - k * 0.03), 0, Math.PI * 2);
      c.fill();
    }
    const p = arcPos(arcs, t);
    // Squash slightly on contact.
    let sq = 0;
    for (const e of xylo.events) {
      if (e.kind === hit && t >= e.t && t - e.t < 0.1) sq = Math.max(sq, (1 - (t - e.t) / 0.1) * e.v);
    }
    c.save();
    c.translate(p.x, p.y + r * 0.16 * sq);
    c.scale(1 + 0.17 * sq, 1 - 0.17 * sq);
    sphere(c, 0, 0, r, a, b, d);
    c.restore();
  };
  drawBall(xylo.arcs, ballR, "#FFFDF4", "#F3D99A", "#A87F3E", "#F3D99A", "top");
  if (t >= xylo.bassStart) drawBall(xylo.bassArcs, bassR, "#F4F4FF", "#AFC3F2", "#4D62A0", "#AFC3F2", "bass");
  FADE(c, t, "#081A25");
};

export const Xylo = () => (
  <Scene draw={drawXylo} audio="xylo">
    <Caption text="Every collision is a note." from={0.3} to={20} color="#DDF3EE" y={240} />
  </Scene>
);
