import { test } from "node:test";
import assert from "node:assert/strict";
import { scheduleDay, forecast, freeSlots, toMin, fromMin } from "../src/scheduler.js";

const settings = { dayStart: "09:00", dayEnd: "13:00", peakStart: "09:00", peakEnd: "11:00", maxFocusMin: 90, breakMin: 15, minChunkMin: 15, bufferPct: 0, workDays: [0, 1, 2, 3, 4, 5, 6] };
const plan = { id: "p1", title: "Plan", priority: 3, status: "active" };
const task = (id, extra = {}) => ({ id, title: id, planId: "p1", estimateMin: 60, priority: 3, status: "todo", actualMin: 0, ...extra });
const taskBlocks = (day) => day.blocks.filter((b) => b.kind === "task");

test("freeSlots subtracts busy intervals", () => {
  assert.deepEqual(freeSlots(0, 100, [{ start: 10, end: 20 }, { start: 15, end: 30 }, { start: 90, end: 120 }]), [
    { start: 0, end: 10 },
    { start: 30, end: 90 },
  ]);
});

test("higher priority work goes first and events are respected", () => {
  const day = scheduleDay({
    date: "2026-10-12",
    settings,
    plans: [plan],
    tasks: [task("low", { priority: 1 }), task("high", { priority: 5 })],
    events: [{ id: "e", title: "Standup", date: "2026-10-12", start: "10:00", end: "10:30" }],
  });
  const tb = taskBlocks(day);
  assert.equal(tb[0].taskId, "high");
  for (const b of tb) assert.ok(b.end <= toMin("10:00") || b.start >= toMin("10:30"), `${fromMin(b.start)} overlaps the event`);
});

test("dependencies are ordered", () => {
  const day = scheduleDay({
    date: "2026-10-12",
    settings,
    plans: [plan],
    tasks: [task("second", { priority: 5, dependsOn: ["first"] }), task("first", { priority: 1 })],
    events: [],
  });
  const ids = taskBlocks(day).map((b) => b.taskId);
  assert.ok(ids.indexOf("first") < ids.indexOf("second"));
});

test("long tasks are split and breaks inserted", () => {
  const day = scheduleDay({ date: "2026-10-12", settings, plans: [plan], tasks: [task("big", { estimateMin: 180 })], events: [] });
  assert.ok(day.blocks.some((b) => b.kind === "break"));
  const total = taskBlocks(day).reduce((a, b) => a + b.end - b.start, 0);
  assert.equal(total, 180);
  for (const b of taskBlocks(day)) assert.ok(b.end - b.start <= 90);
});

test("nothing is scheduled before now, overflow is reported", () => {
  const day = scheduleDay({ date: "2026-10-12", nowMin: toMin("12:00"), settings, plans: [plan], tasks: [task("a", { estimateMin: 120 })], events: [] });
  for (const b of day.blocks) assert.ok(b.start >= toMin("12:00"));
  assert.equal(day.unscheduled[0].remainingMin, 60);
});

test("habits land at their preferred time and only when due", () => {
  const habit = { id: "h", title: "Read", planId: "p1", repeat: "weekdays", estimateMin: 20, preferredTime: "12:00", startDate: "2026-01-01" };
  const mon = scheduleDay({ date: "2026-10-12", settings, plans: [plan], tasks: [habit], events: [] });
  assert.equal(mon.blocks[0].start, toMin("12:00"));
  const sun = scheduleDay({ date: "2026-10-11", settings, plans: [plan], tasks: [habit], events: [] });
  assert.equal(sun.blocks.length, 0);
});

test("paused plans are not scheduled", () => {
  const day = scheduleDay({ date: "2026-10-12", settings, plans: [{ ...plan, status: "paused" }], tasks: [task("a")], events: [] });
  assert.equal(taskBlocks(day).length, 0);
});

test("forecast flags plans that will miss their deadline", () => {
  const tasks = Array.from({ length: 10 }, (_, i) => task(`t${i}`, { estimateMin: 120 })); // 20h of work, 4h/day
  const f = forecast({ fromDate: "2026-10-12", settings, plans: [{ ...plan, deadline: "2026-10-13" }], tasks, events: [] });
  assert.equal(f.plans[0].status, "at_risk");
  assert.ok(f.plans[0].projectedFinish > "2026-10-13");
  const ok = forecast({ fromDate: "2026-10-12", settings, plans: [{ ...plan, deadline: "2026-10-30" }], tasks, events: [] });
  assert.equal(ok.plans[0].status, "on_track");
});

test("a plan's daily cap limits how much of it lands on one day", () => {
  const day = scheduleDay({ date: "2026-10-12", settings, plans: [{ ...plan, dailyMin: 60 }], tasks: [task("a"), task("b")], events: [] });
  assert.equal(taskBlocks(day).reduce((a, b) => a + b.end - b.start, 0), 60);
  assert.equal(day.unscheduled[0].reason, "plan's daily time used up");
});
