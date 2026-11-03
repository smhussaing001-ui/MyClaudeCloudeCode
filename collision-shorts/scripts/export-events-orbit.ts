// Same role as export-events.ts, for the orbit geometry series.
import { mkdirSync, writeFileSync } from "node:fs";
import { WEAVES, geoEvents, roseEvents, weaveEvents } from "../src/sims-orbit.ts";
import type { Ev } from "../src/sims.ts";

mkdirSync("audio-build", { recursive: true });
const save = (name: string, ev: Ev[]) => {
  writeFileSync(`audio-build/${name}.json`, JSON.stringify(ev));
  const kinds = Object.entries(Object.groupBy(ev, (e) => e.kind)).map(([k, v]) => `${k}:${v!.length}`);
  console.log(name.padEnd(14), kinds.join(" "), "last", ev.at(-1)!.t.toFixed(2));
};

for (const w of WEAVES) save(`weave-${w.id}`, weaveEvents(w));
save("geo", geoEvents());
save("rose", roseEvents());
