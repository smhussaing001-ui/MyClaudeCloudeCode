// JSON-file persistence. Writes go to a temp file first and are renamed so a crash can't corrupt the data.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { DEFAULT_SETTINGS } from "./scheduler.js";

const EMPTY = () => ({
  version: 1,
  settings: { ...DEFAULT_SETTINGS },
  plans: [],
  tasks: [],
  events: [],
  schedules: {}, // date -> { blocks, unscheduled, warnings, stats, generatedAt }
  reviews: {}, // date -> { rating, wins, blockers, notes }
  active: null, // { taskId, date, startedAt }
});

export function createStore(file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let db = EMPTY();
  if (fs.existsSync(file)) {
    db = { ...EMPTY(), ...JSON.parse(fs.readFileSync(file, "utf8")) };
    db.settings = { ...DEFAULT_SETTINGS, ...db.settings };
  }
  const save = () => {
    const tmp = `${file}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(db, null, 2));
    fs.renameSync(tmp, file);
  };
  return {
    get: () => db,
    /** Apply a mutation and persist it. */
    update(fn) {
      const out = fn(db);
      save();
      return out;
    },
  };
}

export const newId = (prefix) => `${prefix}_${crypto.randomBytes(5).toString("hex")}`;
