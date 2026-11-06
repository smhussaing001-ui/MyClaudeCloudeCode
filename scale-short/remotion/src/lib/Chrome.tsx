import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, EASE } from "./theme";
import { F } from "./fonts";
import { Starburst } from "./Starburst";

/** Top-left section marker: "06 / OBSERVABLE UNIVERSE". Small, mono, low emphasis. */
export const SectionLabel: React.FC<{ index: string; label?: string; width: number }> = ({
  index,
  label,
  width,
}) => (
  <div
    style={{
      fontFamily: F.mono,
      fontSize: width * 0.026,
      letterSpacing: width * 0.006,
      color: C.white,
      opacity: 0.85,
      whiteSpace: "nowrap",
    }}
  >
    {index}
    {label ? `  /  ${label}` : ""}
  </div>
);

/** Top-right progress scrubber — a hairline rule with an accent tick. */
export const Scrubber: React.FC<{ width: number; progress?: number }> = ({ width, progress }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = progress ?? frame / Math.max(1, durationInFrames - 1);
  const w = width * 0.22;
  const hair = Math.max(1, width * 0.002);
  return (
    <svg width={w} height={width * 0.03} style={{ display: "block", overflow: "visible" }}>
      <line x1={0} y1={width * 0.012} x2={w} y2={width * 0.012} stroke={C.white} strokeWidth={hair} />
      <line
        x1={p * w}
        y1={width * 0.004}
        x2={p * w}
        y2={width * 0.021}
        stroke={C.accent}
        strokeWidth={hair * 2}
      />
    </svg>
  );
};

/**
 * Caption line: accent starburst bullet then one short phrase.
 * The reference shows one phrase at a time, word-synced, in the lower third.
 */
export const Caption: React.FC<{ text: string; width: number; dark?: boolean; delay?: number }> = ({
  text,
  width,
  dark = true,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [delay, delay + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  const rise = interpolate(frame, [delay, delay + 10], [width * 0.012, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: width * 0.028,
        opacity: o,
        translate: `0px ${rise}px`,
      }}
    >
      <Starburst size={width * 0.037} color={C.accent} spokes={12} extend={o} />
      <span
        style={{
          fontFamily: F.sans,
          fontWeight: 700,
          fontSize: width * 0.054,
          color: dark ? C.paper : "#1A1A1A",
          letterSpacing: -width * 0.0005,
        }}
      >
        {text}
      </span>
    </div>
  );
};

/** Small letterspaced unit label sitting above the numerals. */
export const UnitLabel: React.FC<{ text: string; width: number }> = ({ text, width }) => (
  <div
    style={{
      fontFamily: F.mono,
      fontSize: width * 0.03,
      letterSpacing: width * 0.012,
      color: C.paper,
      whiteSpace: "nowrap",
    }}
  >
    {text}
  </div>
);
