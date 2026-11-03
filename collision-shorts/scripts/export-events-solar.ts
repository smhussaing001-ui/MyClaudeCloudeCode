// Same role as export-events.ts, for the solar system series.
import { mkdirSync, writeFileSync } from "node:fs";
import { accretionSim, asteroidEvents, bodeEvents, bounceSim, laplaceEvents } from "../src/sims-solar.ts";
import type { Ev } from "../src/sims.ts";

mkdirSync("audio-build", { recursive: true });
const save = (name: string, ev: Ev[]) => {
  writeFileSync(`audio-build/${name}.json`, JSON.stringify(ev));
  console.log(name.padEnd(10), "events", ev.length, "first", ev[0].t.toFixed(2), "last", ev.at(-1)!.t.toFixed(2));
};

save("bode", bodeEvents());
save("laplace", laplaceEvents());
save("asteroid", asteroidEvents());
save("accretion", accretionSim().events);
save("bounce", bounceSim().events);
