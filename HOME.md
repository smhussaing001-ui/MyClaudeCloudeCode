# HOME — daily operating system

## 1. The daily loop (batch by *who does the work*)

The biggest time win: **Claude's long jobs run while you do hands-on work.** Never sit and watch a
download, a research pass or a render.

| Time | You | Claude (in parallel) |
|---|---|---|
| **Start (15 min)** | Open this file. Pick today's 1 *ship* item + 1–2 *push* items from the board. | Kick off the background jobs for today (see §3): footage downloads, research, script drafts, renders. |
| **Block A — Edit (2–3 h)** | Resolve: cut the ship item. No email, no browsing. | Downloads/research keep running; scripts land as files. |
| **Block B — Review (45 min)** | Read the drafts Claude produced, leave notes in the file or chat. | Revise; build graphics/Fusion comps into the timeline. |
| **Block C — Polish & publish (1 h)** | Thumbnail, title, upload, schedule. | Description, chapters, tags, credits text. |
| **End (5 min)** | Tell Claude "update the board". | Updates §2, writes `HANDOFF.md` in any half-done project. |

Rules: one *ship* item per day gets finished before anything new starts. Max 3 projects "in edit" at once.

## 2. Production board

Stages: `Idea → Research → Script → Assets → Edit → Graphics → Publish → Done`
(statuses below are what the files show as of 2026-11-03 — correct anything stale)

| Project | Format | Stage | Next step |
|---|---|---|---|
| Einstein 22-min | SciSense | Edit / Graphics | Continue marker animations in minimal fog style |
| BB Builds Black House | Lord Gizmo | Script → Edit | Script done (`LordGizmo/lord-gizmo-bb-builds-black-house-script.md`); VO + music in `Footage/BB Builds Black House` |
| One-year apartment renovation | Lord Gizmo | ? | Confirm published or not |
| Lindsay Clancy | Legal-crimes doc | Research done, A9 audit + A10 script outstanding (as of Aug) | Check verdict, run A9 → A10 (prompt in `MASTER_HANDOFF.md`) |
| Unseen World — 10 countries | Unseen World | Assets (clips 01–10 sorted) | Edit |
| Ukraine / Yemen footage | Unseen World | Assets | Dedupe done; edit |
| Collision shorts 01–15 | Science shorts | Rendered | Publish schedule |
| Galaxy scale short | Science shorts | Edit / exports | Check final export |
| Crane short v3 | Science shorts | Rendered v3 | Approve or fix → publish |

## 3. Kickoff prompts (paste into a new Claude session)

**Build narration script (Lord Gizmo)**
> Write a Lord Gizmo script for `<YouTube link or pasted transcript>`. Save to `LordGizmo/lord-gizmo-<slug>.md`.

**Stock footage run (background)**
> Download Envato footage for `<topic/country>`: `<N>` min, 1080p, low-data, 2 at a time, into `Footage/<name>/`. Fix issues yourself, report at the end.

**Doc research (legal-crimes)**
> New legal-crimes episode on `<case>`. Set up `<slug>-doc/` with BRIEF.md and run the 11-agent pipeline with the usual model routing. Stop after A2 for my review.

**SciSense episode**
> New SciSense episode on `<topic>` from `<source>`. Script first (`SciSense/<slug>/script.md`), then a shot list in the minimal fog style.

**Graphics from the timeline**
> Resolve is open on `<project>`. Read the timeline markers and build the graphic for each marker in `<style>`.

**End of day**
> Update the board in HOME.md and write HANDOFF.md for anything half done.

Tip: run text jobs (scripts, research) as **cloud sessions** so they don't tie up this PC; keep
Resolve/Envato/Blender sessions local. Name each session after the project.

## 4. Weekly (Sunday, 30 min)
- Pick next week's 3–5 ship items; fill the board.
- Queue research/script drafts for all of them on Monday morning so Assets/Edit never waits.
- Clear `C:\Users\USER\Downloads`, archive finished projects to `_archive/`, commit + push.
