// Scheduling engine: turns plans + tasks + fixed events into a concrete day.
// Pure functions only (no I/O) so the engine can be tested and reused for forecasting.

export const DEFAULT_SETTINGS = {
  dayStart: "08:00",
  dayEnd: "18:00",
  peakStart: "09:00", // hours when you do your best deep work
  peakEnd: "12:00",
  maxFocusMin: 90, // longest block before a break is inserted
  breakMin: 15,
  minChunkMin: 15, // never schedule a fragment shorter than this
  workDays: [1, 2, 3, 4, 5], // 0 = Sunday
  bufferPct: 10, // keep this % of the day free for the unexpected
};

export function toMin(hhmm) {
  const [h, m] = String(hhmm).split(":").map(Number);
  return h * 60 + (m || 0);
}

export function fromMin(min) {
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function addDays(date, n) {
  const d = new Date(`${date}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export function daysBetween(from, to) {
  return Math.round((Date.parse(`${to}T12:00:00Z`) - Date.parse(`${from}T12:00:00Z`)) / 86400000);
}

export function weekday(date) {
  return new Date(`${date}T12:00:00Z`).getUTCDay();
}

/** Subtract busy intervals from [start, end) and return the free gaps, sorted. */
export function freeSlots(start, end, busy) {
  const sorted = busy
    .map((b) => ({ start: Math.max(start, b.start), end: Math.min(end, b.end) }))
    .filter((b) => b.end > b.start)
    .sort((a, b) => a.start - b.start);
  const slots = [];
  let cursor = start;
  for (const b of sorted) {
    if (b.start > cursor) slots.push({ start: cursor, end: b.start });
    cursor = Math.max(cursor, b.end);
  }
  if (cursor < end) slots.push({ start: cursor, end });
  return slots;
}

export function isHabit(task) {
  return Boolean(task.repeat);
}

export function habitDueOn(task, date) {
  if (!task.repeat) return false;
  if (task.startDate && date < task.startDate) return false;
  const wd = weekday(date);
  if (task.repeat === "daily") return true;
  if (task.repeat === "weekdays") return wd >= 1 && wd <= 5;
  if (task.repeat === "weekly") return wd === weekday(task.startDate || task.createdAt?.slice(0, 10) || date);
  return false;
}

export function remainingMin(task) {
  if (task.status === "done" || task.status === "skipped") return 0;
  return Math.max(0, (task.estimateMin || 30) - (task.actualMin || 0));
}

function effectiveDeadline(task, plan) {
  const candidates = [task.deadline, plan?.deadline].filter(Boolean).sort();
  return candidates[0] || null;
}

/**
 * Priority score for putting `task` into a slot starting at `slotStart` on `date`.
 * Higher is more important. Exported so the UI can explain ordering.
 */
export function scoreTask(task, plan, date, slotStart, settings) {
  let score = (task.priority || 3) * 10 + (plan?.priority || 3) * 6;
  const reasons = [];

  const deadline = effectiveDeadline(task, plan);
  if (deadline) {
    const daysLeft = daysBetween(date, deadline);
    if (daysLeft < 0) {
      score += 60;
      reasons.push("overdue");
    } else {
      score += 40 / (daysLeft + 1);
      if (daysLeft <= 2) reasons.push(`due in ${daysLeft}d`);
    }
  }
  if (task.status === "in_progress" || (task.actualMin || 0) > 0) {
    score += 15;
    reasons.push("already started");
  }
  if (slotStart != null && task.energy) {
    const inPeak = slotStart >= toMin(settings.peakStart) && slotStart < toMin(settings.peakEnd);
    if (task.energy === "high") score += inPeak ? 12 : -6;
    if (task.energy === "low") score += inPeak ? -8 : 4;
  }
  return { score, reasons };
}

/**
 * Build a schedule for one day.
 *
 * @param {object} input
 * @param {string} input.date        YYYY-MM-DD
 * @param {number|null} input.nowMin minutes since midnight; time before it is not scheduled (null = whole day)
 * @param {object} input.settings
 * @param {object[]} input.plans
 * @param {object[]} input.tasks
 * @param {object[]} input.events    fixed calendar events {id,title,date,start,end}
 * @param {object[]} [input.keepBlocks] blocks already in the past that must be preserved
 * @param {Map<string,number>} [input.remaining] override of remaining minutes per task (used by forecast)
 * @param {Set<string>} [input.finished] task ids finished before this day (used by forecast)
 * @returns {{blocks: object[], unscheduled: object[], warnings: string[], stats: object}}
 */
export function scheduleDay(input) {
  const settings = { ...DEFAULT_SETTINGS, ...(input.settings || {}) };
  const { date } = input;
  const plansById = new Map((input.plans || []).map((p) => [p.id, p]));
  const dayStart = toMin(settings.dayStart);
  const dayEnd = toMin(settings.dayEnd);
  const startAt = Math.max(dayStart, input.nowMin == null ? dayStart : Math.ceil(input.nowMin / 5) * 5);

  const blocks = [];
  const warnings = [];
  const keep = (input.keepBlocks || []).filter((b) => b.end <= startAt);
  blocks.push(...keep);

  // Fixed events and pinned tasks are immovable.
  const busy = [];
  for (const ev of input.events || []) {
    if (ev.date !== date) continue;
    const b = { kind: "event", id: ev.id, title: ev.title, start: toMin(ev.start), end: toMin(ev.end) };
    blocks.push(b);
    busy.push(b);
  }
  for (const b of keep) busy.push(b);

  const remaining = new Map();
  const finished = new Set(input.finished || []);
  for (const t of input.tasks || []) {
    if (t.status === "done") finished.add(t.id);
    remaining.set(t.id, input.remaining?.has(t.id) ? input.remaining.get(t.id) : remainingMin(t));
  }

  const activePlan = (t) => {
    if (!t.planId) return true;
    const p = plansById.get(t.planId);
    return p && p.status !== "paused" && p.status !== "archived" && p.status !== "done";
  };

  // Habits: due today, not yet done today, placed at their preferred time when possible.
  const habits = (input.tasks || []).filter(
    (t) => isHabit(t) && activePlan(t) && habitDueOn(t, date) && !(t.doneDates || []).includes(date),
  );
  const habitQueue = [];
  for (const h of habits.sort((a, b) => (a.preferredTime || "99").localeCompare(b.preferredTime || "99"))) {
    const len = h.estimateMin || 15;
    if (h.preferredTime) {
      const s = toMin(h.preferredTime);
      const e = s + len;
      const clash = busy.some((b) => s < b.end && e > b.start);
      if (s >= startAt && e <= dayEnd && !clash) {
        const b = blockFor(h, plansById, s, e, ["habit"]);
        blocks.push(b);
        busy.push(b);
        continue;
      }
    }
    habitQueue.push(h);
  }

  // Pinned tasks (user said "do this at 14:00").
  for (const t of input.tasks || []) {
    if (!t.pinned || t.pinned.date !== date || remaining.get(t.id) <= 0) continue;
    const s = toMin(t.pinned.start);
    const e = s + Math.min(remaining.get(t.id), dayEnd - s);
    if (s < startAt || e <= s) continue;
    const b = blockFor(t, plansById, s, e, ["pinned"]);
    blocks.push(b);
    busy.push(b);
    remaining.set(t.id, remaining.get(t.id) - (e - s));
    if (remaining.get(t.id) <= 0) finished.add(t.id);
  }

  // Capacity buffer: hold back a share of today's free time for the unexpected.
  const slots = freeSlots(startAt, dayEnd, busy);
  const freeTotal = slots.reduce((s, x) => s + x.end - x.start, 0);
  let budget = Math.round(freeTotal * (1 - (settings.bufferPct || 0) / 100));

  const candidates = (input.tasks || []).filter(
    (t) =>
      !isHabit(t) &&
      activePlan(t) &&
      remaining.get(t.id) > 0 &&
      t.status !== "skipped" &&
      !(t.earliestDate && t.earliestDate > date) &&
      !(t.pinned && t.pinned.date === date),
  );

  // Per-plan daily cap so one big plan doesn't crowd out the others.
  const planUsed = new Map();
  const capLeft = (t) => {
    const cap = plansById.get(t.planId)?.dailyMin;
    return cap ? cap - (planUsed.get(t.planId) || 0) : Infinity;
  };

  const depsMet = (t) => (t.dependsOn || []).every((d) => finished.has(d) || !remaining.has(d));

  let focusRun = 0; // minutes of consecutive focus without a break
  for (const slot of slots) {
    let t = slot.start;
    focusRun = 0;
    while (slot.end - t >= settings.minChunkMin && budget >= settings.minChunkMin) {
      if (settings.maxFocusMin - focusRun < settings.minChunkMin) {
        const be = Math.min(slot.end, t + settings.breakMin);
        blocks.push({ kind: "break", title: "Break", start: t, end: be });
        t = be;
        focusRun = 0;
        continue;
      }
      // Habits that missed their preferred time take the first gap.
      if (habitQueue.length) {
        const h = habitQueue[0];
        const len = h.estimateMin || 15;
        if (slot.end - t >= len) {
          habitQueue.shift();
          blocks.push(blockFor(h, plansById, t, t + len, ["habit"]));
          t += len;
          focusRun += len;
          budget -= len;
          continue;
        }
      }
      const room = Math.min(slot.end - t, settings.maxFocusMin - focusRun, budget);
      let best = null;
      for (const task of candidates) {
        const rem = remaining.get(task.id);
        if (rem <= 0 || !depsMet(task)) continue;
        const cap = capLeft(task);
        if (cap < Math.min(rem, settings.minChunkMin)) continue;
        const { score, reasons } = scoreTask(task, plansById.get(task.planId), date, t, settings);
        if (!best || score > best.score) best = { task, score, reasons };
      }
      if (!best) break;
      const rem = remaining.get(best.task.id);
      let len = Math.min(rem, room, capLeft(best.task));
      if (rem - len > 0 && rem - len < settings.minChunkMin && len > settings.minChunkMin) {
        len -= settings.minChunkMin - (rem - len); // leave a schedulable remainder
      }
      len = Math.max(len, Math.min(rem, settings.minChunkMin));
      blocks.push(blockFor(best.task, plansById, t, t + len, best.reasons, rem > len));
      remaining.set(best.task.id, rem - len);
      if (best.task.planId) planUsed.set(best.task.planId, (planUsed.get(best.task.planId) || 0) + len);
      if (rem - len <= 0) finished.add(best.task.id);
      t += len;
      focusRun += len;
      budget -= len;
    }
    if (blocks.at(-1)?.kind === "break" && blocks.at(-1).start >= slot.start) blocks.pop(); // no break before nothing
  }
  for (const h of habitQueue) warnings.push(`No room today for habit “${h.title}”.`);

  const unscheduled = [];
  for (const task of candidates) {
    const rem = remaining.get(task.id);
    if (rem <= 0) continue;
    const plan = plansById.get(task.planId);
    const reason = !depsMet(task)
      ? "waiting on a dependency"
      : capLeft(task) < settings.minChunkMin
        ? "plan's daily time used up"
        : "not enough time today";
    unscheduled.push({ taskId: task.id, title: task.title, planId: task.planId, remainingMin: rem, reason });
    const deadline = effectiveDeadline(task, plan);
    if (deadline && deadline <= date) warnings.push(`“${task.title}” is due ${deadline === date ? "today" : deadline} but doesn't fit.`);
  }

  blocks.sort((a, b) => a.start - b.start);
  const scheduledMin = blocks.filter((b) => b.kind === "task").reduce((s, b) => s + b.end - b.start, 0);
  return {
    date,
    blocks,
    unscheduled,
    warnings,
    stats: { freeMin: freeTotal, scheduledMin, bufferMin: Math.max(0, freeTotal - scheduledMin) },
    remaining,
    finished,
  };
}

function blockFor(task, plansById, start, end, reasons = [], partial = false) {
  const plan = plansById.get(task.planId);
  return {
    kind: "task",
    taskId: task.id,
    planId: task.planId || null,
    title: task.title,
    color: plan?.color || "#64748b",
    start,
    end,
    reasons,
    partial,
    habit: isHabit(task),
  };
}

/**
 * Simulate upcoming days to project when each plan finishes, compared with its deadline.
 */
export function forecast({ fromDate, nowMin = null, settings, plans, tasks, events, horizonDays = 60 }) {
  const s = { ...DEFAULT_SETTINGS, ...(settings || {}) };
  let remaining = null;
  let finished = null;
  const lastWorkDay = new Map(); // planId -> last date work was scheduled
  const days = [];
  for (let i = 0; i < horizonDays; i++) {
    const date = addDays(fromDate, i);
    if (!s.workDays.includes(weekday(date))) continue;
    const day = scheduleDay({
      date,
      nowMin: i === 0 ? nowMin : null,
      settings: s,
      plans,
      tasks,
      events,
      remaining: remaining || undefined,
      finished: finished || undefined,
    });
    remaining = day.remaining;
    finished = day.finished;
    for (const b of day.blocks) if (b.kind === "task" && !b.habit && b.planId) lastWorkDay.set(b.planId, date);
    if (i < 14) days.push({ date, scheduledMin: day.stats.scheduledMin, freeMin: day.stats.freeMin });
    const left = [...remaining.entries()].some(([id, m]) => m > 0 && !isHabit(tasks.find((t) => t.id === id) || {}));
    if (!left) break;
  }
  const result = [];
  for (const plan of plans) {
    const planTasks = tasks.filter((t) => t.planId === plan.id && !isHabit(t));
    const leftMin = planTasks.reduce((acc, t) => acc + (remaining?.get(t.id) ?? remainingMin(t)), 0);
    const totalMin = planTasks.reduce((acc, t) => acc + (t.estimateMin || 30), 0);
    const doneMin = planTasks.filter((t) => t.status === "done").reduce((acc, t) => acc + (t.estimateMin || 30), 0);
    const projected = leftMin > 0 ? null : lastWorkDay.get(plan.id) || (planTasks.length ? fromDate : null);
    let status = "on_track";
    if (plan.status === "paused") status = "paused";
    else if (!planTasks.length) status = "empty";
    else if (planTasks.length && planTasks.every((t) => t.status === "done")) status = "done";
    else if (!projected) status = "beyond_horizon";
    else if (plan.deadline && projected > plan.deadline) status = "at_risk";
    result.push({
      planId: plan.id,
      projectedFinish: projected,
      deadline: plan.deadline || null,
      status,
      progressPct: totalMin ? Math.round((doneMin / totalMin) * 100) : 0,
      remainingMin: planTasks.reduce((acc, t) => acc + remainingMin(t), 0),
    });
  }
  return { plans: result, days };
}
