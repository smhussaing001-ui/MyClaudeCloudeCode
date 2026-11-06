import React from "react";

/**
 * Radial spoke mark. The reference uses a 12-spoke burst as its only
 * recurring accent shape — at caption-bullet size, at mark size on the
 * character's face panel, and as a tick on scales.
 *
 * This is a generic geometric primitive, not a reproduction of anyone's
 * logo; set `spokes` to whatever the project's own mark needs.
 */
export const Starburst: React.FC<{
  size: number;
  color: string;
  spokes?: number;
  thickness?: number;
  /** 0 = spokes retracted to the centre, 1 = full length. */
  extend?: number;
  /** Rounded spoke ends, as in the reference. */
  round?: boolean;
}> = ({ size, color, spokes = 12, thickness, extend = 1, round = true }) => {
  const r = size / 2;
  const w = thickness ?? Math.max(1, size * 0.052);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: "block" }}>
      {Array.from({ length: spokes }, (_, i) => {
        const a = (i / spokes) * Math.PI * 2 - Math.PI / 2;
        const inner = r * 0.08;
        const outer = inner + (r * 0.92 - inner) * extend;
        return (
          <line
            key={i}
            x1={r + Math.cos(a) * inner}
            y1={r + Math.sin(a) * inner}
            x2={r + Math.cos(a) * outer}
            y2={r + Math.sin(a) * outer}
            stroke={color}
            strokeWidth={w}
            strokeLinecap={round ? "round" : "butt"}
          />
        );
      })}
    </svg>
  );
};
