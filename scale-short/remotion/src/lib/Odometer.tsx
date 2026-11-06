import React from "react";
import { interpolate, useCurrentFrame, Easing } from "remotion";
import { C, EASE } from "./theme";
import { F } from "./fonts";

const CYCLES = 3;

/**
 * Rolling numerals. The reference lands big figures with an odometer roll
 * and leaves real motion blur on the digits mid-roll, which is most of what
 * sells it — a clean roll reads as a slot machine, a blurred one reads as
 * a measuring instrument.
 *
 * Digits settle left-to-right so the magnitude resolves before the detail.
 */
export const Odometer: React.FC<{
  value: string;
  size: number;
  color?: string;
  /** Frame range for the whole roll. */
  range?: [number, number];
  stagger?: number;
  /** Shrink to fit this width. Long figures overflow 9:16 otherwise. */
  maxWidth?: number;
}> = ({ value, size, color = C.paper, range = [0, 34], stagger = 2.5, maxWidth }) => {
  const frame = useCurrentFrame();
  const chars = value.split("");
  // Digits are monospaced drums at 0.56em; separators are narrower. Measure
  // the figure in em and scale down if it would run off the frame.
  const DIGIT_EM = 0.56;
  const SEP_EM = 0.3;
  const em = chars.reduce((t, c) => t + (/[0-9]/.test(c) ? DIGIT_EM : SEP_EM), 0);
  if (maxWidth && em * size > maxWidth) size = maxWidth / em;
  const digitIdx = chars.map((c, i) => (/[0-9]/.test(c) ? i : -1)).filter((i) => i >= 0);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-end",
        fontFamily: F.display,
        fontSize: size,
        lineHeight: 1,
        color,
      }}
    >
      {chars.map((ch, i) => {
        if (!/[0-9]/.test(ch)) {
          return (
            <span
              key={i}
              style={{
                lineHeight: 1,
                display: "inline-block",
                width: size * SEP_EM,
                textAlign: "center",
              }}
            >
              {ch}
            </span>
          );
        }
        const order = digitIdx.indexOf(i);
        const start = range[0] + order * stagger;
        const end = range[1] + order * stagger;
        const target = Number(ch);
        const total = CYCLES * 10 + target;

        const pos = interpolate(frame, [start, end], [0, total], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(...EASE),
        });
        // speed in digits/frame -> vertical blur while the drum is spinning
        const prev = interpolate(frame - 1, [start, end], [0, total], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(...EASE),
        });
        const speed = Math.abs(pos - prev);
        const blur = Math.min(size * 0.09, speed * size * 0.085);

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              height: size,
              width: size * DIGIT_EM,
              overflow: "hidden",
              position: "relative",
              filter: blur > 0.3 ? `blur(${blur}px)` : undefined,
            }}
          >
            <span
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                width: "100%",
                translate: `0px ${-(pos % 10) * size}px`,
              }}
            >
              {Array.from({ length: 11 }, (_, d) => (
                <span key={d} style={{ height: size, lineHeight: 1, display: "block" }}>
                  {d % 10}
                </span>
              ))}
            </span>
          </span>
        );
      })}
    </div>
  );
};
