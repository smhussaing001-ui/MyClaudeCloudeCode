# D:\Claude — YouTube production workspace

One person runs several faceless YouTube formats from here. Claude writes scripts, researches,
fetches stock footage, and builds graphics/animations in DaVinci Resolve Studio, Remotion and Blender.
The daily plan and production board live in `HOME.md` — read it at the start of a session and update
its board when a stage finishes.

## Where things live
| Format | Folder | Entry point |
|---|---|---|
| Lord Gizmo / One Man Build (build narration) | `LordGizmo/` (`lord-gizmo-<slug>.md`) | skill `lord-gizmo-script` |
| SciSense science docs | `SciSense/<episode>/` | `script-*.md`, `source-analysis-and-plan.md` |
| Legal-crimes docs | `clancy-doc/` | `MASTER_HANDOFF.md`, `BRIEF.md`, `DECISIONS.md` |
| Unseen World (country/travel) | `UnseenWorld/Clips/`, raw `Footage/<Country>/` | `UnseenWorld/Clips/INDEX.md` |
| Science shorts | `collision-shorts/` (Remotion), `galaxy-scale-short/` (Resolve Fusion), `crane-short/` (Blender) | each folder's scripts |
| Top-10 listicles | `windows_pipeline/` | `KICKOFF.md`, `PLAYBOOK.md`, skill `davinci-top10-autoedit` |
| Veo AI reels | `veo-videos/` (own nested repo) | `README.md`, `SHOT_PLAN.md` |
| Thumbnails | `thumbnails/` | |
| Shared textures | `texture/` | |
| Old/junk files (kept, not deleted) | `_archive/` | |
| Non-YouTube personal files | `_personal/` | |
| Resolve MCP server | `resolve-mcp/` | `README.md` |

New project → its own folder named `<format>-<slug>/` (or inside the format folder), with a
`HANDOFF.md` that says the current stage and the next step. Keep the root clean: only
`CLAUDE.md`, `HOME.md` and config files live there.

## House rules
- Media (video/audio/images/xlsx) is git-ignored; text work syncs to GitHub for cloud sessions. Pull first.
- Resolve, Envato/Chrome and Blender work runs locally only; scripts and research can run in the cloud.
- Fix problems autonomously during long jobs (downloads, renders); report at the end.
- Style/feedback memories (SciSense fog look, no tables, Cox shorts mask, Fusion pitfalls, Envato rules)
  apply — check them before designing.
