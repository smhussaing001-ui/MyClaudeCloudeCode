# scale-short / hyperframes

The same Milky Way short, rebuilt with **HyperFrames** (HeyGen's open-source
HTML-to-MP4 renderer) instead of Remotion. Same script, same measured style,
same red accent — a second implementation of `../SCRIPT-milky-way.md`.

## Render

```bash
cd milky-way
npm i                                   # also vendors gsap into assets/js
python3 build.py                        # regenerate index.html + compositions/
export HYPERFRAMES_BROWSER_PATH=/opt/pw-browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
npx hyperframes check --json            # lint + runtime + layout + motion + contrast
npx hyperframes render . -o out/milky-way-hf.mp4
npx hyperframes snapshot --at 12 --at 47
```

On the Windows workstation drop `HYPERFRAMES_BROWSER_PATH`; HyperFrames finds
its own Chrome.

## Why there is a build.py

HyperFrames compositions are plain HTML, and its contract bans `Math.random()`
and any network fetch — everything on screen must be a function of timeline
time. So every dot in every diagram is computed **at build time** by
`build.py` (seeded mulberry32) and written into the HTML as static SVG. That
is stronger than seeding a PRNG at render time: there is no runtime randomness
left to drift.

`build.py` also holds the 16 beats, so the script and the film stay in one place.

## Things that cost a render to learn

1. **Scene styles are scoped to the `<template>`.** A selector rooted at the
   host id (`#s00 .mark`) is outside that scope and silently never matches,
   while GSAP targeting the same `#s00 .mark` works fine because it queries the
   live assembled document. The symptom was every light scene collapsing to
   the top-left corner. Scene CSS hangs off `#root`.
2. **The scaffold loads GSAP from a CDN**, which both the contract's
   no-network rule and this container's network policy object to. Vendored to
   `assets/js/gsap.min.js`.
3. **Declare intended overflow.** The scale push and the odometer drums both
   leave their boxes on purpose; without `data-layout-allow-overflow` the
   layout check raised 77 findings.
4. **The vertical guide is tighter than the reference.** On 1080x1920 nothing
   readable goes above 168 px or below 1330 px. The Remotion build ran content
   to 1536; this one is rebuilt into the band.

## Verified

`npx hyperframes check` is clean on lint, runtime, layout, motion and contrast.
Against the reference's measured signature:

| | reference | this build |
|---|---|---|
| hard cuts (0.25-0.03) | 0 | 0 |
| light / dark split | 42 / 56 | 38 / 61 |
| accent coverage (mean) | 0.28% | 0.28% |
| accent hue | 16.4 deg | 5.3 deg (red, as asked) |
| frames "nearly still" | 65.3% | 85.3% |

The stillness number is the one that does not match, and it is worse than the
Remotion build's 67.5% on identical content. Adding a slow vertical drift on
top of the scale push changed it by nothing measurable — +-6 px over 5 s is
below what the metric resolves. The cause is not isolated; it is most likely
that GSAP's `power3.out` front-loads motion harder than the Remotion build's
bezier, leaving longer dead tails inside each hold.

## Known gaps

- **No audio.** `check` says so itself (`film_silent`, `audio_none`): a 73 s
  film that tells something should carry a music bed and sound on its visible
  actions. There are no audio assets here and no network to fetch any.
- **26 `line_unread` warnings**, all single digits from the odometer mid-roll.
  Accepted by design — those digits are not meant to be read.
- **The white scenes are still a 2D stand-in**, same as the Remotion build.
