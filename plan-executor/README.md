# Plan Executor

A personal plan executor that runs alongside you all day. It is not a to-do list: you describe a goal, it **designs** a plan, **schedules** that plan into real time slots around your calendar, and **tracks** what actually happens so it can re-plan when the day goes off course.

## Run it

```bash
cd plan-executor
npm install
npm start            # http://localhost:4321
```

To have Claude design plans and coach your day, set an API key before starting:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
npm start
```

Without a key, everything still works. The designer and coach fall back to built-in templates.

| Env var | Default | Purpose |
|---|---|---|
| `PORT` | `4321` | HTTP port |
| `HOST` | `127.0.0.1` | Bind address (use `0.0.0.0` to reach it from your phone on the same network) |
| `PLAN_EXECUTOR_DB` | `data/db.json` | Where your data is stored |
| `PLAN_EXECUTOR_MODEL` | `claude-opus-5-5` | Claude model for design and coaching |

## What it does

### Design
- **Design a plan**: describe a goal, add some context, a deadline and how many minutes a day you can spend on it. Claude returns milestones, tasks that are concrete and sized (15–180 min), dependencies, energy levels, priorities, supporting habits, success criteria and risks.
- You review the draft first. You can change estimates or drop tasks, and nothing is saved until you choose to keep it.
- You can also build plans by hand: milestones, tasks, habits (daily / weekdays / weekly), deadlines, "not before" dates and dependencies.

### Schedule
The engine (`src/scheduler.js`) builds your day:
- It fits work around **fixed events** and your **working hours**.
- Order is set by a score that combines task priority, plan priority, **deadline urgency**, overdue status and work you've already started.
- **Energy matching**: high-energy tasks go into your peak hours and low-energy admin goes elsewhere.
- **Dependencies** are respected. A task waits until the tasks it depends on are done.
- **Per-plan daily caps** let several plans share your day.
- Long tasks are **split into focus blocks**, with **breaks** inserted automatically.
- A **buffer** (10% by default) is kept free for the unexpected.
- Habits go at their preferred time. Tasks can be pinned to an exact time.
- **Replan from now** keeps what is already past and re-plans the rest of the day using what you actually logged. Blocks that slipped get fitted back in.
- **Forecast**: it simulates your upcoming working days to project each plan's finish date. A plan is flagged *at risk* when the projection passes its deadline.

### Track
- The **Now** card shows the current or next block, with Start / Pause / Done / Push to tomorrow.
- A **live timer** records sessions against each task.
- **Block notifications**: you get a browser notification and an in-app toast when each block starts.
- The **Coach** gives a briefing: the most important outcome today, what to protect, concrete adjustments, and the biggest risk.
- **Daily review**: rate the day, note wins and blockers.
- **Insights**: scheduled vs. logged focus, plan adherence, estimate accuracy (how much longer tasks really take), habit streaks, and plan forecasts.

## Layout

```
server.js          REST API + static file server (Node built-ins, no framework)
src/scheduler.js   pure scheduling + forecasting engine
src/ai.js          Claude integration (structured outputs) + template fallbacks
src/store.js       JSON file persistence (atomic writes)
public/            single-page UI (vanilla JS, no build step)
test/              scheduler tests: npm test
```

Your data lives in a single local JSON file (`data/db.json`, git-ignored). Back it up by copying that file.
