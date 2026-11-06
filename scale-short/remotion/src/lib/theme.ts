/**
 * Palette measured off the reference film (see ../../STYLE-SPEC.md).
 * The accent is the one deliberate deviation: the reference orange #E14F18
 * rotated to red and rebalanced to hold the same relative luminance (0.416),
 * so no other value in the frame needed changing.
 */
export const C = {
  accent: "#ED4839", // was #E14F18 — H5 S0.76, luminance-matched
  accentDim: "#8E2B22", // accent at ~40% against the dark field
  dark: "#030303", // the dark field — deliberately not pure black
  paper: "#EFEFE8", // warm off-white, the display/numeral colour
  white: "#FFFFFF", // diagram line art only
  light0: "#DCDCDC", // white-system background gradient, top
  light1: "#EBEBEB", // white-system background gradient, bottom
} as const;

/** Accent coverage in the reference never exceeds ~4.2% of pixels. Keep it scarce. */
export const ACCENT_BUDGET = 0.042;

export const FONT = {
  display: "Anton", // heavy condensed numerals
  mono: "JetBrains Mono", // letterspaced uppercase labels
  sans: "Inter", // caption line
} as const;

/**
 * The reference holds a composition almost perfectly still, then slides.
 * Median inter-frame difference across all 4794 frames is 0.0011.
 */
export const HOLD = { drift: 0.0011 } as const;

/** Editorial ease used throughout — smooth out, no overshoot, nothing springy. */
export const EASE = [0.16, 1, 0.3, 1] as const;
/** Slightly firmer curve for the scene slides. */
export const EASE_SLIDE = [0.65, 0, 0.35, 1] as const;
