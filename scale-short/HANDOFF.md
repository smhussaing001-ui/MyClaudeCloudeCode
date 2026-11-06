# scale-short — HANDOFF

## Stage
Dark infographic system built and rendering in Remotion. 3D pass not started.

## What's here
- `STYLE-SPEC.md` — reverse-engineered spec of the "Time and Infinity" reference short
  (9:16, 160 s, Anthropic brand film). Measured palette, act structure, motion language,
  typography and the orange -> red conversion.
- `remotion/` — the dark infographic system built against that spec. Renders a 28 s
  six-scene sequence at 1080x1920. See `remotion/README.md`.

## Verified against the reference
| | reference | this build |
|---|---|---|
| hard cuts (thresholds 0.25-0.03) | 0 | 0 |
| mean inter-frame difference | 0.0093 | 0.0122 |
| frames "nearly still" | 65.3% | 75.9% |
| light / dark split | 42 / 56 | 49 / 50 |
| accent coverage (mean) | 0.28% | 0.37% |
| accent hue | 16.4 deg (orange) | 4.7 deg (red, as asked) |

## Decided
- Accent moves from the reference **#E14F18** orange to **#ED4839** red
  (luminance-matched, so nothing else needs re-balancing).
- Infographic layer builds in **Remotion** — the `remotion-dev/skills` skill is already
  installed and covers captions, transitions, timing and voiceover.
- White 3D character: Blender pass composited in, or React Three Fiber via the skill's
  `rules/3d.md`. Not yet chosen.

## Next step
The 3D pass for the white scenes — `LightScene` is currently a 2D stand-in.

## Open
- 3D route: Blender pass composited in, vs React Three Fiber in Remotion.
- Typeface for the display numerals (currently Anton; reference is narrower and
  higher-contrast).
- Audio and word-synced captions.
- Closing the remaining stillness gap (75.9% vs 65.3%).
