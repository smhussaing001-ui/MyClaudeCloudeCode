import React from "react";
import { AbsoluteFill, Easing } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { C, EASE_SLIDE } from "../lib/theme";
import { DarkScene, DarkSceneProps } from "./DarkScene";
import { LightScene } from "./LightScene";

const HOLD = 150; // 5s
const SLIDE = 15; // 0.5s

const timing = linearTiming({
  durationInFrames: SLIDE,
  easing: Easing.bezier(...EASE_SLIDE),
});
const up = slide({ direction: "from-bottom" });
const down = slide({ direction: "from-top" });

/** Scene list, in order. `null` entries are the white breathing beats. */
type Beat = { light: string } | DarkSceneProps;

const BEATS: Beat[] = [
  { light: "Tonight, look up." },
  {
    index: "01",
    label: "YOU",
    unit: "PLANET",
    value: "1",
    caption: "You're on one planet.",
    playhead: 0.05,
    datum: "HERE",
    datumAt: 0.06,
    seed: 31,
    visual: "sphere",
    progress: 0.04,
  },
  {
    index: "02",
    label: "THE SUN",
    unit: "LIGHT MINUTES",
    value: "8",
    caption: "Eight minutes of light away.",
    playhead: 0.16,
    datum: "SUN",
    datumAt: 0.16,
    seed: 42,
    visual: "sphere",
    progress: 0.1,
  },
  { light: "Now keep going." },
  {
    index: "03",
    label: "NEXT STAR",
    unit: "LIGHT YEARS",
    value: "4.2",
    caption: "The next one takes four years.",
    playhead: 0.31,
    datum: "PROXIMA",
    datumAt: 0.31,
    seed: 17,
    visual: "sphere",
    progress: 0.2,
  },
  {
    index: "04",
    label: "THE DISC",
    unit: "LIGHT YEARS ACROSS",
    value: "100,000",
    caption: "A hundred thousand across.",
    playhead: 0.62,
    datum: "SUN",
    datumAt: 0.62,
    seed: 5,
    visual: "spiral",
    progress: 0.3,
  },
  { light: "That's where you live." },
  {
    index: "05",
    label: "THE COUNT",
    unit: "STARS",
    value: "400,000,000,000",
    caption: "Nobody has counted them.",
    playhead: 0.74,
    datum: "EST.",
    datumAt: 0.5,
    seed: 9,
    visual: "spiral",
    showMarker: false,
    progress: 0.38,
  },
  { light: "We are not in the middle." },
  {
    index: "06",
    label: "OFF CENTRE",
    unit: "LIGHT YEARS OUT",
    value: "26,000",
    caption: "Out on a quiet arm.",
    playhead: 0.45,
    datum: "CORE",
    datumAt: 0.07,
    seed: 5,
    visual: "spiral",
    markerAt: 0.8,
    progress: 0.5,
  },
  {
    index: "07",
    label: "THE CENTRE",
    unit: "SOLAR MASSES",
    value: "4,300,000",
    caption: "Something sits at the centre.",
    playhead: 0.08,
    datum: "SGR A*",
    datumAt: 0.08,
    seed: 13,
    visual: "contour",
    progress: 0.58,
  },
  {
    index: "08",
    label: "THE ORBIT",
    unit: "YEARS PER LAP",
    value: "225,000,000",
    caption: "One lap: 225 million years.",
    playhead: 0.52,
    datum: "ONE LAP",
    datumAt: 0.52,
    seed: 5,
    visual: "spiral",
    markerAt: 0.8,
    progress: 0.66,
  },
  { light: "We've been here before." },
  {
    index: "09",
    label: "LAST LAP",
    unit: "YEARS AGO",
    value: "230,000,000",
    caption: "Last time: dinosaurs.",
    playhead: 0.12,
    datum: "NOW",
    datumAt: 0.93,
    seed: 21,
    visual: "contour",
    progress: 0.78,
  },
  {
    index: "10",
    label: "INBOUND",
    unit: "YEARS FROM NOW",
    value: "4,500,000,000",
    caption: "Andromeda is coming.",
    playhead: 0.88,
    datum: "NOW",
    datumAt: 0.07,
    seed: 29,
    visual: "contour",
    progress: 0.9,
  },
  { light: "You're on it." },
];

const isLight = (b: Beat): b is { light: string } => "light" in b;

/**
 * Milky Way — 16 scenes, 72.5s, 1080x1920.
 *
 * Same system as Main: no cuts anywhere, vertical slides only, long holds with
 * reveals staggered across them, accent kept scarce. Slide direction flips at
 * the two turns in the script — when we learn we're off-centre, and when
 * Andromeda arrives — so the piece changes direction exactly where the
 * narration does.
 */
export const MilkyWay: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: C.dark }}>
      <TransitionSeries>
        {BEATS.map((b, i) => (
          <React.Fragment key={i}>
            {i > 0 ? (
              <TransitionSeries.Transition
                presentation={i === 8 || i === 13 ? down : up}
                timing={timing}
              />
            ) : null}
            <TransitionSeries.Sequence durationInFrames={HOLD}>
              {isLight(b) ? <LightScene caption={b.light} /> : <DarkScene {...b} />}
            </TransitionSeries.Sequence>
          </React.Fragment>
        ))}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
