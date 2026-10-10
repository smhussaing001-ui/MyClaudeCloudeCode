// Plan Executor server: REST API + static UI. Zero-config: `npm start`, then open http://localhost:4321
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createStore, newId } from "./src/store.js";
import { scheduleDay, forecast, fromMin, toMin, addDays, isHabit, habitDueOn, DEFAULT_SETTINGS } from "./src/scheduler.js";
import { designPlan, dailyBrief, aiConfigured } from "./src/ai.js";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 4321);
const HOST = process.env.HOST || "127.0.0.1";
const store = createStore(process.env.PLAN_EXECUTOR_DB || path.join(ROOT, "data", "db.json"));

const PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"];
const PLAN_FIELDS = ["title", "why", "successCriteria", "deadline", "priority", "color", "status", "milestones", "dailyMin"];
const TASK_FIELDS = [
  "title", "notes", "planId", "milestoneId", "estimateMin", "priority", "energy", "dependsOn",
  "earliestDate", "deadline", "status", "repeat", "preferredTime", "startDate", "pinned",
];

const pick = (obj, keys) => Object.fromEntries(keys.filter((k) => obj[k] !== undefined).map((k) => [k, obj[k]]));
const today = () => new Date().toISOString().slice(0, 10);

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

function findOr404(list, id, what) {
  const item = list.find((x) => x.id === id);
  if (!item) throw new HttpError(404, `${what} not found`);
  return item;
}

function newTask(db, body) {
  if (!body.title?.trim()) throw new HttpError(400, "title is required");
  const task = {
    id: newId("task"),
    status: "todo",
    estimateMin: 30,
    priority: 3,
    energy: "medium",
    dependsOn: [],
    actualMin: 0,
    sessions: [],
    doneDates: [],
    createdAt: new Date().toISOString(),
    ...pick(body, TASK_FIELDS),
  };
  task.title = task.title.trim();
  task.estimateMin = Math.max(5, Number(task.estimateMin) || 30);
  if (task.repeat && !task.startDate) task.startDate = body.today || today();
  db.tasks.push(task);
  return task;
}

/** Close the running timer, if any, and credit the time to its task. */
function stopActive(db) {
  if (!db.active) return null;
  const task = db.tasks.find((t) => t.id === db.active.taskId);
  const end = new Date();
  const min = Math.round((end - new Date(db.active.startedAt)) / 60000);
  if (task && min >= 1) {
    task.sessions.push({ date: db.active.date, start: db.active.startedAt, end: end.toISOString(), min });
    if (!isHabit(task)) task.actualMin = (task.actualMin || 0) + min;
  }
  const stopped = { ...db.active, min };
  db.active = null;
  return stopped;
}

function buildSchedule(db, { date, nowMin, replan }) {
  const prev = db.schedules[date];
  const keepBlocks =
    replan && prev && nowMin != null ? storedBlocksAsMinutes(prev).filter((b) => b.end <= nowMin && b.kind !== "event") : [];
  const day = scheduleDay({ date, nowMin, settings: db.settings, plans: db.plans, tasks: db.tasks, events: db.events, keepBlocks });
  const schedule = {
    blocks: day.blocks.map((b) => ({ ...b, start: fromMin(b.start), end: fromMin(b.end) })),
    unscheduled: day.unscheduled,
    warnings: day.warnings,
    stats: day.stats,
    generatedAt: new Date().toISOString(),
    replannedAt: replan ? fromMin(nowMin ?? 0) : null,
  };
  db.schedules[date] = schedule;
  return schedule;
}

function storedBlocksAsMinutes(schedule) {
  return (schedule?.blocks || []).map((b) => ({ ...b, start: toMin(b.start), end: toMin(b.end) }));
}

function computeForecast(db, date, nowMin) {
  const f = forecast({ fromDate: date, nowMin, settings: db.settings, plans: db.plans, tasks: db.tasks, events: db.events });
  return { ...f, plans: f.plans.map((p) => ({ ...p, title: db.plans.find((x) => x.id === p.planId)?.title })) };
}

function insights(db, date, days = 14) {
  const series = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = addDays(date, -i);
    const focusMin = db.tasks.flatMap((t) => t.sessions || []).filter((s) => s.date === d).reduce((a, s) => a + s.min, 0);
    const completed = db.tasks.filter((t) => t.completedOn === d).length + db.tasks.filter((t) => (t.doneDates || []).includes(d)).length;
    const plannedMin = db.schedules[d]?.stats?.scheduledMin || 0;
    series.push({ date: d, focusMin, completed, plannedMin, rating: db.reviews[d]?.rating || null });
  }
  const measured = db.tasks.filter((t) => t.status === "done" && !isHabit(t) && t.actualMin > 0);
  const estimateRatio = measured.length
    ? measured.reduce((a, t) => a + t.actualMin / t.estimateMin, 0) / measured.length
    : null;
  const habits = db.tasks.filter(isHabit).map((h) => {
    let streak = 0;
    for (let i = 0, d = date; i < 365; i++, d = addDays(d, -1)) {
      if (!habitDueOn(h, d)) continue;
      if ((h.doneDates || []).includes(d)) streak++;
      else if (d !== date) break; // today isn't over yet
    }
    return { taskId: h.id, title: h.title, streak, doneToday: (h.doneDates || []).includes(date) };
  });
  return { series, estimateRatio, measuredTasks: measured.length, habits };
}

function importDesign(db, body) {
  const d = body.design;
  if (!d?.title) throw new HttpError(400, "design.title is required");
  const plan = {
    id: newId("plan"),
    title: d.title,
    why: d.why || "",
    successCriteria: d.successCriteria || [],
    deadline: body.deadline || d.suggestedDeadline || null,
    priority: Number(body.priority) || 3,
    dailyMin: Number(body.minutesPerDay) || null,
    color: body.color || PALETTE[db.plans.length % PALETTE.length],
    status: "active",
    milestones: [],
    risks: d.risks || [],
    createdAt: new Date().toISOString(),
  };
  db.plans.push(plan);
  const keyToId = new Map();
  const created = [];
  for (const m of d.milestones || []) {
    const milestone = { id: newId("ms"), title: m.title };
    plan.milestones.push(milestone);
    for (const t of m.tasks || []) {
      const task = newTask(db, { ...t, planId: plan.id, milestoneId: milestone.id, dependsOn: [] });
      task.priority = Math.min(5, Math.max(1, Math.round(t.priority || 3)));
      keyToId.set(t.key, task.id);
      created.push([task, t.dependsOn || []]);
    }
  }
  for (const [task, deps] of created) task.dependsOn = deps.map((k) => keyToId.get(k)).filter(Boolean);
  for (const h of d.habits || []) {
    newTask(db, { ...h, preferredTime: h.preferredTime || undefined, planId: plan.id, today: body.today });
  }
  return plan;
}

// ---- Routing -----------------------------------------------------------------

const routes = [];
const route = (method, pattern, handler) => {
  const keys = [];
  const re = new RegExp(`^${pattern.replace(/:(\w+)/g, (_, k) => (keys.push(k), "([^/]+)"))}$`);
  routes.push({ method, re, keys, handler });
};

route("GET", "/api/state", () => ({ ...store.get(), aiConfigured: aiConfigured() }));

route("PUT", "/api/settings", ({ body }) =>
  store.update((db) => (db.settings = { ...db.settings, ...pick(body, Object.keys(DEFAULT_SETTINGS)) })),
);

route("POST", "/api/plans", ({ body }) =>
  store.update((db) => {
    if (!body.title?.trim()) throw new HttpError(400, "title is required");
    const plan = {
      id: newId("plan"),
      status: "active",
      priority: 3,
      milestones: [],
      successCriteria: [],
      color: PALETTE[db.plans.length % PALETTE.length],
      createdAt: new Date().toISOString(),
      ...pick(body, PLAN_FIELDS),
    };
    db.plans.push(plan);
    return plan;
  }),
);
route("PATCH", "/api/plans/:id", ({ params, body }) =>
  store.update((db) => Object.assign(findOr404(db.plans, params.id, "plan"), pick(body, PLAN_FIELDS))),
);
route("DELETE", "/api/plans/:id", ({ params }) =>
  store.update((db) => {
    findOr404(db.plans, params.id, "plan");
    db.plans = db.plans.filter((p) => p.id !== params.id);
    const gone = new Set(db.tasks.filter((t) => t.planId === params.id).map((t) => t.id));
    db.tasks = db.tasks.filter((t) => !gone.has(t.id));
    if (db.active && gone.has(db.active.taskId)) db.active = null;
    return { ok: true };
  }),
);
route("POST", "/api/plans/import", ({ body }) => store.update((db) => importDesign(db, body)));

route("POST", "/api/tasks", ({ body }) => store.update((db) => newTask(db, body)));
route("PATCH", "/api/tasks/:id", ({ params, body }) =>
  store.update((db) => {
    const task = findOr404(db.tasks, params.id, "task");
    Object.assign(task, pick(body, TASK_FIELDS));
    if (body.status === "done" && !task.completedOn) task.completedOn = body.today || today();
    if (body.status && body.status !== "done") delete task.completedOn;
    return task;
  }),
);
route("DELETE", "/api/tasks/:id", ({ params }) =>
  store.update((db) => {
    findOr404(db.tasks, params.id, "task");
    db.tasks = db.tasks.filter((t) => t.id !== params.id);
    for (const t of db.tasks) t.dependsOn = (t.dependsOn || []).filter((d) => d !== params.id);
    if (db.active?.taskId === params.id) db.active = null;
    return { ok: true };
  }),
);

route("POST", "/api/tasks/:id/start", ({ params, body }) =>
  store.update((db) => {
    const task = findOr404(db.tasks, params.id, "task");
    stopActive(db);
    db.active = { taskId: task.id, date: body.date || today(), startedAt: new Date().toISOString() };
    if (!isHabit(task) && task.status === "todo") task.status = "in_progress";
    return db.active;
  }),
);
route("POST", "/api/timer/stop", () => store.update((db) => stopActive(db) || { ok: true }));
route("POST", "/api/tasks/:id/complete", ({ params, body }) =>
  store.update((db) => {
    const task = findOr404(db.tasks, params.id, "task");
    const date = body.date || today();
    if (db.active?.taskId === task.id) stopActive(db);
    if (isHabit(task)) {
      task.doneDates = [...new Set([...(task.doneDates || []), date])];
    } else {
      task.status = "done";
      task.completedOn = date;
    }
    return task;
  }),
);
route("POST", "/api/tasks/:id/uncomplete", ({ params, body }) =>
  store.update((db) => {
    const task = findOr404(db.tasks, params.id, "task");
    if (isHabit(task)) task.doneDates = (task.doneDates || []).filter((d) => d !== (body.date || today()));
    else {
      task.status = task.actualMin > 0 ? "in_progress" : "todo";
      delete task.completedOn;
    }
    return task;
  }),
);

route("POST", "/api/events", ({ body }) =>
  store.update((db) => {
    if (!body.title || !body.date || !body.start || !body.end) throw new HttpError(400, "title, date, start, end are required");
    if (toMin(body.end) <= toMin(body.start)) throw new HttpError(400, "end must be after start");
    const ev = { id: newId("ev"), ...pick(body, ["title", "date", "start", "end"]) };
    db.events.push(ev);
    return ev;
  }),
);
route("DELETE", "/api/events/:id", ({ params }) =>
  store.update((db) => {
    db.events = db.events.filter((e) => e.id !== params.id);
    return { ok: true };
  }),
);

route("POST", "/api/schedule", ({ body }) =>
  store.update((db) => {
    const date = body.date || today();
    const nowMin = body.nowMin ?? null;
    const schedule = buildSchedule(db, { date, nowMin, replan: Boolean(body.replan) });
    return { schedule, forecast: computeForecast(db, date, nowMin) };
  }),
);
route("GET", "/api/forecast", ({ query }) => {
  const db = store.get();
  return computeForecast(db, query.get("date") || today(), query.has("nowMin") ? Number(query.get("nowMin")) : null);
});
route("GET", "/api/insights", ({ query }) => insights(store.get(), query.get("date") || today()));

route("PUT", "/api/reviews/:date", ({ params, body }) =>
  store.update((db) => (db.reviews[params.date] = { ...pick(body, ["rating", "wins", "blockers", "notes"]), savedAt: new Date().toISOString() })),
);

route("POST", "/api/ai/design", async ({ body }) => {
  if (!body.goal?.trim()) throw new HttpError(400, "goal is required");
  return designPlan({ ...body, today: body.today || today() });
});
route("POST", "/api/ai/brief", async ({ body }) => {
  const db = store.get();
  const date = body.date || today();
  const sched = db.schedules[date];
  const taskById = new Map(db.tasks.map((t) => [t.id, t]));
  const snapshot = {
    date,
    now: body.nowMin != null ? fromMin(body.nowMin) : null,
    schedule: (sched?.blocks || []).map((b) => {
      const t = taskById.get(b.taskId);
      const done = t && (isHabit(t) ? (t.doneDates || []).includes(date) : t.status === "done");
      return { kind: b.kind, title: b.title, start: b.start, end: b.end, status: done ? "done" : t?.status };
    }),
    unscheduled: sched?.unscheduled || [],
    forecast: computeForecast(db, date, body.nowMin ?? null).plans,
    yesterday: db.reviews[addDays(date, -1)] || null,
    insights: insights(db, date, 7),
  };
  return dailyBrief(snapshot);
});

// ---- HTTP plumbing -----------------------------------------------------------

const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".json": "application/json" };

function serveStatic(req, res, pathname) {
  const file = path.join(ROOT, "public", pathname === "/" ? "index.html" : pathname);
  if (!file.startsWith(path.join(ROOT, "public")) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
    res.writeHead(404).end("Not found");
    return;
  }
  res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream" });
  fs.createReadStream(file).pipe(res);
}

async function readBody(req) {
  let raw = "";
  for await (const chunk of req) raw += chunk;
  if (!raw) return {};
  try {
    return JSON.parse(raw);
  } catch {
    throw new HttpError(400, "invalid JSON body");
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  if (!url.pathname.startsWith("/api/")) return serveStatic(req, res, url.pathname);
  try {
    for (const r of routes) {
      const m = r.method === req.method && url.pathname.match(r.re);
      if (!m) continue;
      const params = Object.fromEntries(r.keys.map((k, i) => [k, decodeURIComponent(m[i + 1])]));
      const body = req.method === "GET" ? {} : await readBody(req);
      const out = await r.handler({ params, body, query: url.searchParams });
      res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(out ?? { ok: true }));
      return;
    }
    throw new HttpError(404, "no such endpoint");
  } catch (err) {
    const status = err.status || 500;
    if (status === 500) console.error(err);
    res.writeHead(status, { "Content-Type": "application/json" }).end(JSON.stringify({ error: err.message }));
  }
});

server.listen(PORT, HOST, () => {
  console.log(`Plan Executor running at http://${HOST}:${PORT}`);
  console.log(aiConfigured() ? "Claude is connected for plan design and coaching." : "No ANTHROPIC_API_KEY set — AI features use built-in templates.");
});
