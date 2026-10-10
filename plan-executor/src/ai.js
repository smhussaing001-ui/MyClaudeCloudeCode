// AI layer: Claude designs plans and coaches the day. Falls back to templates when no credentials are set.
import Anthropic from "@anthropic-ai/sdk";
import { betaZodOutputFormat } from "@anthropic-ai/sdk/helpers/beta/zod";
import { z } from "zod";

const MODEL = process.env.PLAN_EXECUTOR_MODEL || "claude-opus-5-5";

let client = null;
function getClient() {
  client ??= new Anthropic();
  return client;
}

export function aiConfigured() {
  return Boolean(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN || process.env.ANTHROPIC_PROFILE);
}

const DesignedPlan = z.object({
  title: z.string(),
  why: z.string().describe("One sentence: the outcome this plan delivers and why it matters"),
  successCriteria: z.array(z.string()),
  suggestedDeadline: z.string().describe("YYYY-MM-DD, realistic given the daily time available"),
  milestones: z.array(
    z.object({
      title: z.string(),
      tasks: z.array(
        z.object({
          key: z.string().describe("Short unique id, e.g. t1"),
          title: z.string().describe("Concrete, verb-first action"),
          notes: z.string(),
          estimateMin: z.number().describe("Realistic minutes, 15-180"),
          energy: z.enum(["high", "medium", "low"]),
          priority: z.number().describe("1 (low) to 5 (critical)"),
          dependsOn: z.array(z.string()).describe("keys of tasks that must finish first"),
        }),
      ),
    }),
  ),
  habits: z.array(
    z.object({
      title: z.string(),
      estimateMin: z.number(),
      repeat: z.enum(["daily", "weekdays", "weekly"]),
      preferredTime: z.string().describe("HH:MM, or empty string for any time"),
    }),
  ),
  risks: z.array(z.string()),
});

const Brief = z.object({
  headline: z.string().describe("One line naming the day's single most important outcome"),
  focus: z.array(z.string()).describe("2-4 things to protect today, in order"),
  adjustments: z.array(z.string()).describe("Concrete schedule changes worth making, or empty"),
  risk: z.string().describe("The biggest threat to the plan right now, or empty"),
  encouragement: z.string(),
});

async function ask(system, user, format) {
  const response = await getClient().beta.messages.parse({
    model: MODEL,
    max_tokens: 16000,
    betas: ["server-side-fallback-2026-07-01"],
    fallbacks: "default",
    thinking: { type: "adaptive" },
    output_config: { effort: "medium", format: betaZodOutputFormat(format) },
    system,
    messages: [{ role: "user", content: user }],
  });
  if (response.stop_reason === "refusal") throw new Error("The model declined this request.");
  if (response.stop_reason === "max_tokens") throw new Error("The response was cut off; try a narrower goal.");
  if (!response.parsed_output) throw new Error("The model returned an unreadable plan.");
  return response.parsed_output;
}

const DESIGN_SYSTEM = `You are an expert planner who turns goals into executable plans.
Break the goal into 2-6 milestones, each with concrete tasks a person can start without further thinking.
Keep tasks between 15 and 180 minutes; split anything bigger. Estimates should be honest, not optimistic.
Use dependsOn only for real ordering constraints. Mark deep, creative or hard tasks as high energy and admin as low.
Suggest habits only when steady daily practice clearly drives the goal.
Fit the total work to the minutes per day the person has, and pick a deadline that leaves slack.`;

export async function designPlan({ goal, context, deadline, minutesPerDay, today }) {
  if (!aiConfigured()) return { source: "template", plan: templatePlan({ goal, deadline, today }) };
  const user = [
    `Goal: ${goal}`,
    context && `Context: ${context}`,
    `Today: ${today}`,
    deadline ? `Deadline: ${deadline}` : "No fixed deadline; suggest one.",
    `Time available for this goal: about ${minutesPerDay || 120} minutes per working day.`,
  ]
    .filter(Boolean)
    .join("\n");
  const plan = await ask(DESIGN_SYSTEM, user, DesignedPlan);
  if (deadline) plan.suggestedDeadline = deadline;
  return { source: "claude", plan };
}

const BRIEF_SYSTEM = `You are a calm, direct execution coach. You see today's schedule, progress and plan forecasts.
Name what matters most, flag what is slipping, and suggest specific adjustments (move, drop, shrink, split).
Be brief and concrete; refer to tasks by title. No generic productivity advice.`;

export async function dailyBrief(snapshot) {
  if (!aiConfigured()) return { source: "template", brief: templateBrief(snapshot) };
  const brief = await ask(BRIEF_SYSTEM, JSON.stringify(snapshot, null, 2), Brief);
  return { source: "claude", brief };
}

// ---- Fallbacks (no API key) -------------------------------------------------

function templatePlan({ goal, deadline, today }) {
  const d = new Date(`${today}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 21);
  return {
    title: goal.length > 60 ? `${goal.slice(0, 57)}…` : goal,
    why: `Deliver: ${goal}`,
    successCriteria: ["The outcome is finished and reviewed", "Lessons are written down"],
    suggestedDeadline: deadline || d.toISOString().slice(0, 10),
    milestones: [
      {
        title: "Clarify",
        tasks: [
          { key: "t1", title: "Define what 'done' looks like", notes: "Write 3 measurable success criteria.", estimateMin: 30, energy: "high", priority: 5, dependsOn: [] },
          { key: "t2", title: "Research and gather inputs", notes: "Collect what you need to start.", estimateMin: 60, energy: "medium", priority: 4, dependsOn: ["t1"] },
        ],
      },
      {
        title: "Build",
        tasks: [
          { key: "t3", title: "Outline the work into steps", notes: "Edit this plan with your real steps.", estimateMin: 45, energy: "high", priority: 4, dependsOn: ["t2"] },
          { key: "t4", title: "Do the first major piece", notes: "", estimateMin: 120, energy: "high", priority: 4, dependsOn: ["t3"] },
          { key: "t5", title: "Do the second major piece", notes: "", estimateMin: 120, energy: "high", priority: 3, dependsOn: ["t4"] },
        ],
      },
      {
        title: "Finish",
        tasks: [
          { key: "t6", title: "Review against success criteria", notes: "", estimateMin: 45, energy: "medium", priority: 4, dependsOn: ["t5"] },
          { key: "t7", title: "Ship it and write a short retro", notes: "", estimateMin: 30, energy: "low", priority: 3, dependsOn: ["t6"] },
        ],
      },
    ],
    habits: [],
    risks: ["This is a generic template — set ANTHROPIC_API_KEY to have Claude design a plan specific to your goal."],
  };
}

function templateBrief(s) {
  const firstTask = s.schedule?.find((b) => b.kind === "task" && b.status !== "done");
  const atRisk = (s.forecast || []).filter((p) => p.status === "at_risk");
  return {
    headline: firstTask ? `Start with “${firstTask.title}” at ${firstTask.start}.` : "Your day is open — plan it or add tasks.",
    focus: (s.schedule || []).filter((b) => b.kind === "task").slice(0, 3).map((b) => b.title),
    adjustments: (s.unscheduled || []).slice(0, 3).map((u) => `“${u.title}” didn't fit (${u.reason}).`),
    risk: atRisk.length ? `${atRisk.map((p) => p.title).join(", ")} projected to miss the deadline.` : "",
    encouragement: "One block at a time.",
  };
}
