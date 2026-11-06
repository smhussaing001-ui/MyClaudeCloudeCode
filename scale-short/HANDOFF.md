# scale-short — HANDOFF

## Stage
Style analysis complete. Nothing built yet.

## What's here
- `STYLE-SPEC.md` — reverse-engineered spec of the "Time and Infinity" reference short
  (9:16, 160 s, Anthropic brand film). Measured palette, act structure, motion language,
  typography and the orange -> red conversion.

## Decided
- Accent moves from the reference **#E14F18** orange to **#ED4839** red
  (luminance-matched, so nothing else needs re-balancing).
- Infographic layer builds in **Remotion** — the `remotion-dev/skills` skill is already
  installed and covers captions, transitions, timing and voiceover.
- White 3D character: Blender pass composited in, or React Three Fiber via the skill's
  `rules/3d.md`. Not yet chosen.

## Next step
Scaffold the Remotion project and build one dark-scene module — ruler + playhead +
odometer numerals + asterisk caption — as a vertical slice to prove the look before
committing to the full runtime.

## Open
- 3D route: Blender vs React Three Fiber.
- Typeface for the display numerals (reference uses a heavy condensed high-contrast face).
- Whether the no-cut, vertical-slide structure is kept for the whole piece.
