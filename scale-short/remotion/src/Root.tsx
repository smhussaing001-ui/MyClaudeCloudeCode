import React from "react";
import { Composition, Still } from "remotion";
import { Main } from "./scenes/Main";
import { MilkyWay } from "./scenes/MilkyWay";
import { DarkScene } from "./scenes/DarkScene";
import { LightScene } from "./scenes/LightScene";

const W = 1080;
const H = 1920;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Main"
        component={Main}
        durationInFrames={855}
        fps={30}
        width={W}
        height={H}
      />
      <Composition
        id="MilkyWay"
        component={MilkyWay}
        durationInFrames={2175}
        fps={30}
        width={W}
        height={H}
      />
      <Composition
        id="DarkScene"
        component={DarkScene}
        durationInFrames={150}
        fps={30}
        width={W}
        height={H}
        defaultProps={{
          index: "06",
          label: "OBSERVABLE UNIVERSE",
          unit: "METRES",
          value: "93",
          caption: "The observable",
          playhead: 0.86,
          seed: 7,
          visual: "sphere" as const,
          progress: 0.55,
        }}
      />
      <Composition
        id="SpiralTest"
        component={DarkScene}
        durationInFrames={150}
        fps={30}
        width={W}
        height={H}
        defaultProps={{
          index: "04",
          label: "THE DISC",
          unit: "LIGHT YEARS ACROSS",
          value: "100,000",
          caption: "A hundred thousand across.",
          playhead: 0.62,
          seed: 5,
          visual: "spiral" as const,
          datum: "SUN",
          datumAt: 0.62,
          progress: 0.4,
        }}
      />
      <Still
        id="LightScene"
        component={LightScene}
        width={W}
        height={H}
        defaultProps={{ caption: "Then let's look closer." }}
      />
    </>
  );
};
