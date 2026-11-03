// Writes every scene's collision times to JSON so the audio lands on the exact frame.
import { mkdirSync, writeFileSync } from "node:fs";
import { cradleEvents, galtonSim, GALTON, piSim, ringSim, xyloSim, type Ev } from "../src/sims.ts";

mkdirSync("audio-build", { recursive: true });
const save = (name: string, ev: Ev[]) => {
  writeFileSync(`audio-build/${name}.json`, JSON.stringify(ev));
  const peak = new Array(20).fill(0);
  ev.forEach((e) => {
    if (e.t < 20) peak[Math.floor(e.t)]++;
  });
  console.log(name.padEnd(8), "events", String(ev.length).padStart(5), "per-sec", peak.join(" "));
};

save("cradle", cradleEvents());
const ring = ringSim();
save("ring", ring.events);
const pi = piSim();
console.log("pi hit counts", pi.map((r) => r.count));
save("pi", pi.flatMap((r, run) => r.events.map((e) => ({ ...e, run, frac: e.i / r.count }))));
const g = galtonSim();
console.log("galton bins", g.fill.join(" "), "of", GALTON.count, "last land", g.events.filter((e) => e.kind === "land").at(-1)?.t);
save("galton", g.events);
save("xylo", xyloSim().events);
