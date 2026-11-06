import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import { C, EASE } from "../lib/theme";
import { F } from "../lib/fonts";
import { Ruler } from "../lib/Ruler";
import { Odometer } from "../lib/Odometer";
import { Caption, SectionLabel, Scrubber, UnitLabel } from "../lib/Chrome";
import { DottedSphere, ContourField } from "../lib/Diagram";

export type DarkSceneProps = {
  index: string;
  label?: string;
  unit: string;
  value: string;
  caption: string;
  playhead: number;
  datum?: string;
  datumAt?: number;
  rightLabel?: string;
  seed?: number;
  visual?: "sphere" | "contour" | "none";
  progress?: number;
};

/**
 * The dark infographic scene: section marker, scrubber, a drawn diagram,
 * a scale bar with the accent playhead, the figure, and one caption line.
 *
 * Everything readable sits in a reserved slot in a single column; only the
 * contour texture is absolutely positioned behind.
 */
export const DarkScene: React.FC<DarkSceneProps> = ({
  index,
  label,
  unit,
  value,
  caption,
  playhead,
  datum = "1 m",
  datumAt = 0.33,
  rightLabel,
  seed = 7,
  visual = "sphere",
  progress,
}) => {
  const { width, height } = useVideoConfig();
  const frame = useCurrentFrame();

  // The reference is never perfectly frozen: its median inter-frame difference
  // is 0.0011, not 0. A locked-off render measures 0.0000 and reads dead on a
  // phone, so every scene gets a slow push plus a hair of drift. Measured
  // against the reference, this is the difference between "still" and "stalled".
  const push = interpolate(frame, [0, 150], [1, 1.07], {
    extrapolateLeft: "clamp",
    extrapolateRight: "extend",
    easing: Easing.bezier(0.4, 0, 0.6, 1),
  });
  const drift = Math.sin(frame / 95) * width * 0.004;

  const chromeO = interpolate(frame, [0, 12], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(...EASE),
  });

  const sphereSize = width * 0.66;

  return (
    <AbsoluteFill style={{ backgroundColor: C.dark }}>
      {visual === "contour" ? (
        <AbsoluteFill
          style={{
            alignItems: "center",
            justifyContent: "flex-start",
            scale: String(1 + (push - 1) * 0.55),
          }}
        >
          <ContourField width={width} height={height} seed={seed} />
        </AbsoluteFill>
      ) : null}

      <AbsoluteFill
        style={{
          paddingTop: height * 0.052,
          paddingBottom: height * 0.2,
          paddingLeft: width * 0.075,
          paddingRight: width * 0.075,
          display: "flex",
          flexDirection: "column",
          translate: `0px ${drift}px`,
          scale: String(push),
        }}
      >
        {/* top chrome */}
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            opacity: chromeO,
          }}
        >
          <SectionLabel index={index} label={label} width={width} />
          <Scrubber width={width} progress={progress} />
        </div>

        {/* diagram slot */}
        <div
          style={{
            flex: 1,
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            minHeight: 0,
            marginBottom: -height * 0.03,
          }}
        >
          {visual === "sphere" ? <DottedSphere size={sphereSize} seed={seed} range={[4, 100]} /> : null}
        </div>

        {/* scale bar — full-bleed, allowed to run off the right edge */}
        <div
          style={{
            marginLeft: -width * 0.075,
            marginRight: -width * 0.075,
            marginBottom: height * 0.022,
            width: width * 1.06,
          }}
        >
          <Ruler
            width={width * 1.06}
            to={playhead}
            range={[10, 86]}
            datum={datum}
            datumAt={datumAt}
            rightLabel={rightLabel}
          />
        </div>

        {/* figure */}
        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: width * 0.004 }}>
            <div style={{ display: "flex", alignItems: "center", gap: width * 0.03 }}>
              <span
                style={{
                  fontFamily: F.display,
                  fontSize: width * 0.062,
                  color: C.accent,
                  lineHeight: 0.8,
                }}
              >
                ≈
              </span>
              <UnitLabel text={unit} width={width} />
            </div>
            <Odometer
              value={value}
              size={width * 0.3}
              maxWidth={width * 0.86}
              range={[6, 62]}
              stagger={4}
            />
          </div>
        </div>

        {/* caption */}
        <div style={{ marginTop: height * 0.028 }}>
          <Caption text={caption} width={width} delay={26} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
