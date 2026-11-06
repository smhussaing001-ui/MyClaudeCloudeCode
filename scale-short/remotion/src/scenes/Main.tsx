import React from "react";
import { AbsoluteFill, Easing } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { C, EASE_SLIDE } from "../lib/theme";
import { DarkScene } from "./DarkScene";
import { LightScene } from "./LightScene";

const HOLD = 150; // 5s — the reference sits on a composition for 3-8s
const SLIDE = 15; // 0.5s, matching the measured ~half-screen move

/**
 * The reference contains zero hard cuts across its full 160s — scene
 * detection finds nothing at thresholds from 0.25 down to 0.03. Scenes change
 * by sliding vertically. So: no cuts here either, only `slide`.
 *
 * It also alternates light and dark almost evenly (measured 42% light /
 * 56% dark), which is why the white scenes are interleaved rather than
 * bunched at the ends.
 */
const timing = linearTiming({
  durationInFrames: SLIDE,
  easing: Easing.bezier(...EASE_SLIDE),
});

const up = slide({ direction: "from-bottom" });
const down = slide({ direction: "from-top" });

export const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: C.dark }}>
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={HOLD}>
          <LightScene caption="Then let's look closer." />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={up} timing={timing} />

        <TransitionSeries.Sequence durationInFrames={HOLD}>
          <DarkScene
            index="04"
            label="GRAIN OF SAND"
            unit="METRES"
            value="0.01"
            caption="Polygons, sand,"
            playhead={0.38}
            seed={11}
            visual="sphere"
            progress={0.2}
          />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={up} timing={timing} />

        <TransitionSeries.Sequence durationInFrames={HOLD}>
          <LightScene caption="And inside a quark?" spokes={12} />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={up} timing={timing} />

        <TransitionSeries.Sequence durationInFrames={HOLD}>
          <DarkScene
            index="06"
            label="OBSERVABLE UNIVERSE"
            unit="METRES"
            value="93"
            caption="The observable"
            playhead={0.86}
            seed={7}
            visual="sphere"
            progress={0.55}
          />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={down} timing={timing} />

        <TransitionSeries.Sequence durationInFrames={HOLD}>
          <DarkScene
            index="09"
            label="BIG BANG"
            unit="YEARS AGO"
            value="13,800,000,000"
            caption="the Big Bang."
            playhead={0.07}
            datum="NOW"
            datumAt={0.92}
            seed={23}
            visual="contour"
            progress={0.82}
          />
        </TransitionSeries.Sequence>

        <TransitionSeries.Transition presentation={up} timing={timing} />

        <TransitionSeries.Sequence durationInFrames={HOLD}>
          <LightScene caption="They opened." />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
