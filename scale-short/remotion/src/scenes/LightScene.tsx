import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, EASE } from "../lib/theme";
import { Caption } from "../lib/Chrome";
import { Starburst } from "../lib/Starburst";

/**
 * The white system. In the reference this slot holds a low-poly 3D character
 * lit by a soft upper-left key against an infinite cyclorama, with the accent
 * mark on its face panel.
 *
 * This is the 2D stand-in: the measured background gradient, the soft floor
 * shadow and the mark, so the light/dark alternation and the accent budget
 * can be judged. The character itself still needs a 3D pass.
 */
export const LightScene: React.FC<{ caption?: string; spokes?: number }> = ({
  caption,
  spokes = 12,
}) => {
  const { width, height } = useVideoConfig();
  const frame = useCurrentFrame();

  const extend = interpolate(frame, [4, 64], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });
  const drift = Math.sin(frame / 110) * width * 0.005;
  const push = interpolate(frame, [0, 150], [1, 1.07], {
    extrapolateLeft: "clamp",
    extrapolateRight: "extend",
    easing: Easing.bezier(0.4, 0, 0.6, 1),
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, ${C.light1} 0%, ${C.light0} 62%, #D4D4D4 100%)`,
      }}
    >
      {/* Cyclorama floor falloff. Kept very light: with no 3D object in the
          slot yet, a strong contact shadow reads as a smudge rather than as
          something standing on the floor. */}
      <AbsoluteFill
        style={{
          top: height * 0.68,
          background: `linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.045) 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          translate: `0px ${drift}px`,
          scale: String(push),
        }}
      >
        <Starburst size={width * 0.3} color={C.accent} spokes={spokes} extend={extend} />
      </AbsoluteFill>
      {caption ? (
        <AbsoluteFill
          style={{
            justifyContent: "flex-end",
            alignItems: "flex-start",
            paddingLeft: width * 0.075,
            paddingBottom: height * 0.075,
          }}
        >
          <Caption text={caption} width={width} dark={false} delay={30} />
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};
