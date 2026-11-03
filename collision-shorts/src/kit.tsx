import { loadFont } from "@remotion/google-fonts/Fraunces";
import { Audio } from "@remotion/media";
import React, { useLayoutEffect, useRef } from "react";
import { AbsoluteFill, staticFile, useCurrentFrame } from "remotion";
import { FPS, H, W, smooth } from "./sims";

export const { fontFamily } = loadFont("normal", { weights: ["300", "400"], subsets: ["latin"] });

export type Ctx = CanvasRenderingContext2D;

export const hexA = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
};

export const background = (c: Ctx, top: string, bottom: string, glow: string, glowY = 960) => {
  const g = c.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, top);
  g.addColorStop(1, bottom);
  c.fillStyle = g;
  c.fillRect(0, 0, W, H);
  const r = c.createRadialGradient(540, glowY, 40, 540, glowY, 900);
  r.addColorStop(0, glow);
  r.addColorStop(1, hexA(top, 0));
  c.fillStyle = r;
  c.fillRect(0, 0, W, H);
};

export const sphere = (c: Ctx, x: number, y: number, r: number, light: string, mid: string, dark: string) => {
  const g = c.createRadialGradient(x - r * 0.36, y - r * 0.42, r * 0.04, x, y, r * 1.04);
  g.addColorStop(0, light);
  g.addColorStop(0.45, mid);
  g.addColorStop(1, dark);
  c.fillStyle = g;
  c.beginPath();
  c.arc(x, y, r, 0, Math.PI * 2);
  c.fill();
};

export const glow = (c: Ctx, x: number, y: number, r: number, hex: string, a: number, mode: GlobalCompositeOperation = "lighter") => {
  if (a <= 0.002 || r <= 0) return;
  c.save();
  c.globalCompositeOperation = mode;
  const g = c.createRadialGradient(x, y, 0, x, y, r);
  g.addColorStop(0, hexA(hex, a));
  g.addColorStop(1, hexA(hex, 0));
  c.fillStyle = g;
  c.fillRect(x - r, y - r, r * 2, r * 2);
  c.restore();
};

export const ripple = (c: Ctx, x: number, y: number, age: number, hex: string, size = 170, life = 0.9) => {
  if (age < 0 || age > life) return;
  const u = age / life;
  const e = 1 - (1 - u) * (1 - u);
  c.strokeStyle = hexA(hex, 0.55 * (1 - u) * (1 - u));
  c.lineWidth = 3 * (1 - u) + 0.6;
  c.beginPath();
  c.arc(x, y, 8 + size * e, 0, Math.PI * 2);
  c.stroke();
};

export const Scene: React.FC<{
  draw: (c: Ctx, t: number, f: number) => void;
  audio: string;
  children?: React.ReactNode;
}> = ({ draw, audio, children }) => {
  const frame = useCurrentFrame();
  const ref = useRef<HTMLCanvasElement>(null);
  useLayoutEffect(() => {
    const c = ref.current!.getContext("2d")!;
    c.setTransform(1, 0, 0, 1, 0, 0);
    draw(c, frame / FPS, frame);
  }, [frame, draw]);
  return (
    <AbsoluteFill>
      <canvas ref={ref} width={W} height={H} style={{ position: "absolute", inset: 0 }} />
      {children}
      <Audio src={staticFile(`audio/${audio}.wav`)} />
    </AbsoluteFill>
  );
};

// Title text sits inside the Shorts safe area (clear of the top bar and bottom UI).
export const Caption: React.FC<{
  text: string;
  from: number;
  to: number;
  color: string;
  y?: number;
  size?: number;
}> = ({ text, from, to, color, y = 250, size = 66 }) => {
  const t = useCurrentFrame() / FPS;
  const opacity = smooth(from, from + 0.7, t) * (1 - smooth(to - 0.6, to, t));
  if (opacity <= 0) return null;
  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: 90,
        right: 90,
        textAlign: "center",
        fontFamily,
        fontWeight: 300,
        fontSize: size,
        lineHeight: 1.15,
        color,
        opacity,
        translate: `0 ${(1 - smooth(from, from + 0.9, t)) * 16}px`,
      }}
    >
      {text}
    </div>
  );
};
