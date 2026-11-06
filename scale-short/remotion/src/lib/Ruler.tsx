import React from "react";
import { interpolate, useCurrentFrame, Easing } from "remotion";
import { C, EASE } from "./theme";
import { F } from "./fonts";

/**
 * Scale bar with an accent playhead — the reference's most repeated device.
 *
 * Geometry taken from the reference: the rule sits at the TOP of the band and
 * the ticks hang downward from it; the bar runs full-bleed and is allowed to
 * leave the frame on the right, which is what stops it reading as a boxed
 * chart. The diagram above sits directly on the rule.
 */
export const Ruler: React.FC<{
  width: number;
  /** Playhead position, 0-1 across the bar. */
  to: number;
  from?: number;
  /** Frame range over which the playhead travels. */
  range?: [number, number];
  datum?: string;
  /** Fractional position of the labelled datum tick. */
  datumAt?: number;
  rightLabel?: string;
  tickCount?: number;
}> = ({
  width,
  to,
  from = 0.08,
  range = [0, 40],
  datum = "1 m",
  datumAt = 0.33,
  rightLabel,
  tickCount = 56,
}) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, range, [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });

  const H = width * 0.1;
  const base = H * 0.16; // the rule, near the top of the band
  const minor = H * 0.17;
  const major = H * 0.36;
  const hair = Math.max(1, width * 0.0019);
  const labelY = base + major + H * 0.1;

  return (
    <div style={{ position: "relative", width, height: H * 1.25 }}>
      <svg width={width} height={H * 1.25} style={{ display: "block", overflow: "visible" }}>
        <line x1={0} y1={base} x2={width} y2={base} stroke={C.white} strokeWidth={hair} />
        {/* left end cap, taller and straddling the rule */}
        <line x1={hair} y1={base - major * 0.75} x2={hair} y2={base + major} stroke={C.white} strokeWidth={hair} />
        {Array.from({ length: tickCount }, (_, i) => {
          const x = (i / (tickCount - 1)) * width;
          const tall = i % 5 === 0;
          return (
            <line
              key={i}
              x1={x}
              y1={base}
              x2={x}
              y2={base + (tall ? minor * 1.55 : minor)}
              stroke={C.white}
              strokeWidth={hair}
            />
          );
        })}
        {/* labelled datum: a long tick straddling the rule */}
        <line
          x1={datumAt * width}
          y1={base - major * 0.55}
          x2={datumAt * width}
          y2={base + major}
          stroke={C.white}
          strokeWidth={hair}
        />
      </svg>

      <div
        style={{
          position: "absolute",
          left: datumAt * width,
          top: labelY,
          translate: "-50% 0",
          fontFamily: F.mono,
          fontSize: width * 0.028,
          color: C.white,
          letterSpacing: width * 0.006,
          whiteSpace: "nowrap",
        }}
      >
        {datum}
      </div>

      {rightLabel ? (
        <div
          style={{
            position: "absolute",
            right: width * 0.02,
            top: labelY,
            fontFamily: F.mono,
            fontSize: width * 0.028,
            color: C.white,
            letterSpacing: width * 0.006,
          }}
        >
          {rightLabel}
        </div>
      ) : null}

      {/* accent playhead: dot sitting on the rule, stem hanging below */}
      <svg
        width={width}
        height={H * 1.25}
        style={{ position: "absolute", left: 0, top: 0, display: "block", overflow: "visible" }}
      >
        <line
          x1={p * width}
          y1={base}
          x2={p * width}
          y2={base + major * 1.5}
          stroke={C.accent}
          strokeWidth={hair * 1.8}
        />
        <circle cx={p * width} cy={base} r={width * 0.0185} fill={C.accent} />
      </svg>
    </div>
  );
};
