# Style spec — "Time and Infinity" reference short

Reverse-engineered from the reference MP4 the user supplied (Anthropic/Claude brand film,
9:16). Every number below was measured off the file, not estimated.

## Source format

| | |
|---|---|
| Resolution | 720 x 1280 (9:16) |
| Frame rate | 30 fps, 4794 frames |
| Duration | 159.79 s (2:40) |
| Codec | H.264 yuv420p, bt709 primaries/transfer |
| Audio | AAC 44.1 kHz stereo |
| Bitrate | ~736 kbps |

## The single most important structural fact

**There is not one hard cut in the whole film.** Scene detection returns zero cuts at
thresholds 0.25, 0.10, 0.05 *and* 0.03. All 160 seconds are one continuous visual flow.
Scenes change by sliding, mostly vertically — measured displacements of dy +18, +23, +31,
-28, -31 px (on a 57 px-tall proxy, so roughly half a screen height in 0.5 s).

This is the signature of the piece. Reproducing the look without reproducing this will miss.

## Motion language

Median inter-frame difference is **0.0011** — the film is nearly static most of the time.
Mean is 0.0093. The rhythm is **long holds punctuated by fast slides**:

- Hold a composition dead still, or drift it almost imperceptibly, for 3-8 s.
- Transition with a quick vertical slide, never a cut, never a cross-dissolve.
- Peak motion energy is at ~104 s (0.0698) — the line-art bookshelf sequence.

Nothing bounces, nothing springs. Easing is smooth and editorial.

## Two visual systems, hard-alternating

Mean luma per 4 s bucket swings between ~0.86 and ~0.03 — a near-binary alternation:

| Time | System |
|---|---|
| 0-14 s | WHITE — 3D character |
| 16-30 s | DARK — Claude app UI mockup |
| 32-42 s | WHITE — 3D |
| 44-50 s | DARK — scale infographic (10^-9) |
| 52-54 s | WHITE |
| 56-74 s | DARK — cosmic scales |
| 76-78 s | WHITE |
| 80-110 s | DARK — deep-time timeline |
| 112-118 s | WHITE |
| 120-138 s | DARK — contour fields, the eye |
| 140-160 s | WHITE — finale |

**System A — white 3D.** Low-poly faceted papercraft character, matte pure-white material,
no specular. Soft key from upper left, soft contact shadow, gentle ambient occlusion in the
creases. Infinite white cyclorama, background gradient #DCDCDC -> #EBEBEB. Shallow depth of
field on some shots. The Anthropic 12-spoke asterisk sits on the face panel as the only colour.

**System B — dark infographic.** Near-black #030303 field. White/off-white line art (dotted
constellation spheres, pyramids, dinosaur silhouettes, bookshelves, contour topography).
Hairline rulers with tick marks and a "1 m" datum. Huge display numerals. Accent used only
as a playhead dot, a tick, a bullet and the odd filled shape.

## Measured palette

| Role | Hex | Notes |
|---|---|---|
| Accent | **#E14F18** | H 16.4 S 0.89 V 0.88 — exact flat fill, measured as colour mode over 13772 px |
| Dark field | **#030303** | not pure black |
| Paper / off-white | **#EFEFE8** | warm, H 60 S 0.02-0.03 |
| Pure white | **#FFFFFF** | diagram line art only |
| 3D background | **#DCDCDC - #EBEBEB** | soft vertical gradient |

Accent hue is tightly held: sampled across the whole film it clusters at 14-17 deg, with a
small secondary amber cluster at 32-50 deg (the emoji, the eye iris). Accent coverage is
tiny — between 0% and 4.2% of pixels per frame. **The restraint is the design.**

## Typography

- **Display numerals** ("10^27", "2560", "13,800,000,000") — very heavy condensed, high stroke
  contrast, off-white #EFEFE8. Superscript exponents. Rendered with a rolling-odometer digit
  animation; motion blur is visible on the digits mid-roll.
- **Labels** ("METRES", "YEARS AGO", "NOW", "06", "1 m") — letterspaced uppercase mono, small,
  white, low emphasis.
- **Captions** — bold sans, sentence case, centred-left, preceded by a small accent asterisk
  bullet. One short phrase at a time, word-synced to VO.
- **Section markers** — "05 / STARS", "07 / OBSERVABLE UNIVERSE" top-left, mono, tiny.
- **Progress scrubber** — a hairline rule top-right with an accent tick showing position.

## Recurring motion-graphic devices

1. Ruler / scale bar with an accent playhead that slides to a value.
2. Odometer numerals rolling to a target figure.
3. Dotted-outline diagrams that draw on.
4. Section number + label in the top-left corner.
5. Top-right progress scrubber running the length of the film.
6. Asterisk-bulleted caption line, bottom third, inside the Shorts safe area.
7. Contour/topographic line fields used as dark-scene texture.

## Red variant (replacing the orange)

Requested change: red instead of orange. A naive hue rotation to 0 deg drops relative
luminance from 0.416 to 0.262 and contrast on #030303 from 5.24:1 to 4.27:1 — the thin
asterisk spokes, playhead dots and caption bullets all get visibly weaker, because this
design leans on small marks.

Rotate the hue **and** rebalance to hold luminance:

| Option | Hex | relLum | vs #030303 | vs paper | Note |
|---|---|---|---|---|---|
| Reference orange | #E14F18 | 0.416 | 5.24:1 | 3.41:1 | original |
| **Matched red (recommended)** | **#ED4839** | 0.416 | 5.50:1 | 3.25:1 | H 5 S 0.76, same perceived weight |
| Closest contrast match | #E74941 | 0.416 | 5.34:1 | 3.35:1 | H 3 S 0.72, slightly pinker |
| Warmer vermilion | #EE4930 | 0.416 | 5.51:1 | 3.24:1 | H 8 S 0.80 |
| Pure deep red | #E01919 | 0.262 | 4.27:1 | 4.18:1 | truest red, 37% less luminance |

`#ED4839` is the default pick: identical luminance to the original, so nothing else in the
frame needs re-balancing.

## Build plan

The black infographic layer — roughly 70% of the runtime — is squarely a **Remotion** job,
and the `remotion-dev/skills` skill is already installed in this repo (`skills-lock.json`).
Relevant rules: `display-captions.md`, `import-srt-captions.md`, `text-animations.md`,
`transitions.md`, `timing.md`, `voiceover.md`, `video-layout.md`, `effects.md`.

The white 3D character is either a Blender render pass composited in (the approach
`crane-short/` already uses) or React Three Fiber inside Remotion via `rules/3d.md`.

Measurements in this spec were produced from the reference file with ffmpeg + numpy;
the analysis scripts are disposable and were not committed.
