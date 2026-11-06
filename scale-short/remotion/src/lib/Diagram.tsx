import React, { useMemo } from "react";
import { interpolate, useCurrentFrame, Easing } from "remotion";
import { C, EASE } from "./theme";

const mulberry = (seed: number) => () => {
  seed |= 0;
  seed = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};

/**
 * Dotted-outline sphere. The reference draws structures as rings of small
 * white dots rather than solid strokes, with one accent dot marking "you are
 * here". Dots reveal progressively rather than fading in as a block.
 */
export const DottedSphere: React.FC<{
  size: number;
  seed?: number;
  blobs?: number;
  /** Frame range over which dots appear. */
  range?: [number, number];
}> = ({ size, seed = 7, blobs = 5, range = [0, 50] }) => {
  const frame = useCurrentFrame();
  const r = size / 2;
  const dotR = size * 0.0062;

  const pts = useMemo(() => {
    const rnd = mulberry(seed);
    const out: { x: number; y: number }[] = [];
    // Dots are spaced by arc length, not by a fixed count, so a big structure
    // and a small one read with the same dot density — that even texture is
    // what makes the reference look drawn rather than scattered.
    const SPACING = size * 0.0165;
    for (let b = 0; b < blobs; b++) {
      // spread centres around the disc by angle slot + jittered radius, so
      // the structures reach the rim instead of bunching in the middle
      const pa = ((b + rnd() * 0.85) / blobs) * Math.PI * 2;
      const pd = (0.18 + Math.sqrt(rnd()) * 0.52) * r;
      const cx = r + Math.cos(pa) * pd;
      const cy = r + Math.sin(pa) * pd;
      const rad = r * (0.13 + rnd() * 0.19);
      const w1 = 0.24 + rnd() * 0.3;
      const w2 = 0.12 + rnd() * 0.22;
      const ph = rnd() * 6.28;
      const lobes = 2 + Math.floor(rnd() * 3);
      const shape = (a: number) =>
        rad * (1 + w1 * Math.sin(a * lobes + ph) + w2 * Math.sin(a * (lobes + 2) - ph));
      // perimeter estimate -> dot count, for uniform spacing
      let per = 0;
      const S = 160;
      let px = cx + shape(0);
      let py = cy;
      for (let k = 1; k <= S; k++) {
        const a = (k / S) * Math.PI * 2;
        const rr = shape(a);
        const x = cx + Math.cos(a) * rr;
        const y = cy + Math.sin(a) * rr;
        per += Math.hypot(x - px, y - py);
        px = x;
        py = y;
      }
      const n = Math.max(12, Math.round(per / SPACING));
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2;
        const rr = shape(a);
        const x = cx + Math.cos(a) * rr;
        const y = cy + Math.sin(a) * rr;
        if (Math.hypot(x - r, y - r) < r * 0.93) out.push({ x, y });
      }
    }
    return out;
  }, [seed, blobs, r, size]);

  const shown = interpolate(frame, range, [0, pts.length], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  const arc = interpolate(frame, [range[0], range[1] * 0.75], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  const circ = 2 * Math.PI * (r * 0.96);

  return (
    <svg width={size} height={size} style={{ display: "block", overflow: "visible" }}>
      <circle
        cx={r}
        cy={r}
        r={r * 0.96}
        fill="none"
        stroke={C.white}
        strokeWidth={size * 0.0085}
        strokeLinecap="round"
        strokeDasharray={`${circ * 0.82} ${circ}`}
        strokeDashoffset={circ * (1 - arc) * 0.82}
        transform={`rotate(-95 ${r} ${r})`}
      />
      {pts.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={dotR} fill={C.white} opacity={i < shown ? 1 : 0} />
      ))}
      {/* "you are here" */}
      <circle cx={r} cy={r} r={size * 0.016} fill={C.accent} opacity={arc} />
    </svg>
  );
};

/**
 * Contour field — the topographic line texture the reference uses to fill
 * dark scenes. Concentric warped rings, very low contrast.
 */
export const ContourField: React.FC<{
  width: number;
  height: number;
  rings?: number;
  seed?: number;
}> = ({ width, height, rings = 26, seed = 3 }) => {
  const frame = useCurrentFrame();
  const cx = width / 2;
  const cy = height * 0.46;
  const paths = useMemo(() => {
    const rnd = mulberry(seed);
    const ph = [rnd() * 6.28, rnd() * 6.28, rnd() * 6.28];
    return Array.from({ length: rings }, (_, i) => {
      const base = (i + 1) * (width / rings) * 0.56;
      const n = 90;
      let d = "";
      for (let k = 0; k <= n; k++) {
        const a = (k / n) * Math.PI * 2;
        const rr =
          base *
          (1 +
            0.12 * Math.sin(a * 2 + ph[0] + i * 0.12) +
            0.07 * Math.sin(a * 3 - ph[1] - i * 0.08) +
            0.04 * Math.sin(a * 5 + ph[2]));
        const x = cx + Math.cos(a) * rr;
        const y = cy + Math.sin(a) * rr * 0.82;
        d += `${k === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)} `;
      }
      return d + "Z";
    });
  }, [rings, seed, width, cx, cy]);

  const o = interpolate(frame, [0, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });

  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      {paths.map((d, i) => (
        <path
          key={i}
          d={d}
          fill="none"
          stroke={i % 7 === 3 ? C.accentDim : "#2A2A2A"}
          strokeWidth={Math.max(1, width * 0.0014)}
          opacity={o * (i % 7 === 3 ? 0.55 : 0.75)}
        />
      ))}
    </svg>
  );
};

/**
 * Dotted spiral galaxy, seen face-on. Logarithmic arms sampled at uniform arc
 * length so dot density stays even from core to rim — the same rule the
 * sphere uses, and the thing that makes these read as drawn rather than
 * scattered. Core is denser; an accent mark sits out on one arm.
 */
export const DottedSpiral: React.FC<{
  size: number;
  arms?: number;
  seed?: number;
  /** Frame range over which the arms draw outward. */
  range?: [number, number];
  /** Fraction along an arm where the accent "you are here" sits, 0-1. */
  markerAt?: number;
  showMarker?: boolean;
}> = ({ size, arms = 4, seed = 5, range = [0, 60], markerAt = 0.8, showMarker = true }) => {
  const frame = useCurrentFrame();
  const r = size / 2;
  const dotR = size * 0.0055;

  const { pts, core, marker } = useMemo(() => {
    const rnd = mulberry(seed);
    const P: { x: number; y: number; d: number; o: number }[] = [];
    const B = 0.26; // spiral tightness
    const TURN = 2.5; // radians of sweep per arm
    let mk = { x: r, y: r };
    for (let a = 0; a < arms; a++) {
      const off = (a / arms) * Math.PI * 2;
      const steps = 240;
      for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const th = t * TURN * Math.PI;
        const rad = r * 0.1 * Math.exp(B * th);
        if (rad > r * 0.95) break;
        // scatter thickens the arm outward, as in a real disc
        const spread = size * (0.003 + t * 0.03);
        const n = 1;
        for (let k = 0; k < n; k++) {
          const jx = (rnd() - 0.5) * spread * 2;
          const jy = (rnd() - 0.5) * spread * 2;
          const x = r + Math.cos(th + off) * rad + jx;
          const y = r + Math.sin(th + off) * rad + jy;
          if (Math.hypot(x - r, y - r) < r * 0.97) P.push({ x, y, d: t, o: 0.5 + rnd() * 0.5 });
        }
        if (a === 1 && Math.abs(t - markerAt) < 1 / steps) {
          mk = { x: r + Math.cos(th + off) * rad, y: r + Math.sin(th + off) * rad };
        }
      }
    }
    // core bulge
    const Cd: { x: number; y: number; o: number }[] = [];
    for (let i = 0; i < 85; i++) {
      const a2 = rnd() * Math.PI * 2;
      const d2 = Math.pow(rnd(), 2.3) * r * 0.13;
      Cd.push({ x: r + Math.cos(a2) * d2, y: r + Math.sin(a2) * d2 * 0.88, o: 0.45 + rnd() * 0.55 });
    }
    return { pts: P, core: Cd, marker: mk };
  }, [seed, arms, r, size, markerAt]);

  // arms draw from the core outward
  const grown = interpolate(frame, range, [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  const coreO = interpolate(frame, [range[0], range[0] + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  const mO = interpolate(frame, [range[1] * 0.75, range[1] * 0.75 + 16], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });

  return (
    <svg width={size} height={size} style={{ display: "block", overflow: "visible" }}>
      {core.map((p, i) => (
        <circle key={`c${i}`} cx={p.x} cy={p.y} r={dotR * 1.15} fill={C.white} opacity={p.o * coreO} />
      ))}
      {pts.map((p, i) =>
        p.d <= grown ? (
          <circle key={i} cx={p.x} cy={p.y} r={dotR} fill={C.white} opacity={p.o} />
        ) : null,
      )}
      {showMarker ? (
        <g opacity={mO}>
          <circle cx={marker.x} cy={marker.y} r={size * 0.014} fill={C.accent} />
          <circle
            cx={marker.x}
            cy={marker.y}
            r={size * 0.045}
            fill="none"
            stroke={C.accent}
            strokeWidth={size * 0.0035}
            opacity={0.65}
          />
        </g>
      ) : null}
    </svg>
  );
};
