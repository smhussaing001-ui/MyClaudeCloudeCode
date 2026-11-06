# scale-short / remotion

The dark infographic system from the reference film, rebuilt in Remotion.
Measurements it is built against are in `../STYLE-SPEC.md`.

## Render

Remotion needs a Chrome binary. This container has one from Playwright:

```bash
export REMOTION_BROWSER_EXECUTABLE=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome
npx remotion render Main out/main.mp4 --browser-executable="$REMOTION_BROWSER_EXECUTABLE"
npx remotion still DarkScene out/frame.png --frame=60 --browser-executable="$REMOTION_BROWSER_EXECUTABLE"
npx remotion studio
```

On the Windows workstation drop the `--browser-executable` flag; Remotion
downloads its own Chrome Headless Shell there.

## What's here

| File | Role |
|---|---|
| `src/lib/theme.ts` | the measured palette, the red accent, the shared easings |
| `src/lib/Ruler.tsx` | scale bar, downward ticks, labelled datum, accent playhead |
| `src/lib/Odometer.tsx` | rolling numerals with speed-derived motion blur, auto-fit |
| `src/lib/Diagram.tsx` | dotted sphere + contour field |
| `src/lib/Chrome.tsx` | section marker, progress scrubber, caption, unit label |
| `src/lib/Starburst.tsx` | generic radial spoke mark (configurable spoke count) |
| `src/scenes/DarkScene.tsx` | the full dark infographic scene |
| `src/scenes/LightScene.tsx` | white cyclorama scene — **2D stand-in, no 3D yet** |
| `src/scenes/Main.tsx` | six scenes, slide transitions, zero cuts |

## Rules this build follows

These came out of measuring the reference, and are the things worth keeping:

1. **No cuts, ever.** Scenes slide vertically. The reference has zero cuts at
   detection thresholds from 0.25 down to 0.03, and so does this.
2. **Nothing is ever perfectly frozen.** A locked-off render measures a median
   inter-frame difference of 0.0000 and reads dead; the reference measures
   0.0011. Every scene gets a slow push plus a hair of drift.
3. **Reveals spread across the hold.** Finishing every animation in the first
   1.5s leaves 3.5s of frozen frame. Diagram, playhead and numerals run on
   staggered ranges that cover most of the hold.
4. **The accent stays scarce.** Reference accent coverage averages 0.28% of
   pixels and never exceeds ~4%. Past that it stops reading as an accent.
5. **The scale bar runs full-bleed** off the right edge. Inset on both sides,
   it reads as a boxed chart instead of a measuring instrument.

## Known gaps

- **No 3D.** `LightScene` is a 2D stand-in. The reference's white scenes are a
  low-poly character under a soft upper-left key on an infinite cyclorama.
  Either a Blender pass composited in, or React Three Fiber via the skill's
  `rules/3d.md`.
- **Still stiller than the reference.** 75.9% of frames measure "nearly still"
  against the reference's 65.3%.
- **No audio**, so no word-synced captions yet. The skill's
  `transcribe-captions.md` / `display-captions.md` cover that path.
- Display face is Anton. The reference uses a narrower, higher-contrast face.
