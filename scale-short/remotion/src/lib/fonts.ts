import { loadFont as loadAnton } from "@remotion/google-fonts/Anton";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

export const anton = loadAnton();
export const mono = loadMono();
export const inter = loadInter();

export const F = {
  display: anton.fontFamily,
  mono: mono.fontFamily,
  sans: inter.fontFamily,
};
