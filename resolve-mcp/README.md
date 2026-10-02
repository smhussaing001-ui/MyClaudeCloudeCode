# DaVinci Resolve MCP Server

Lets you command Claude to read and control a running DaVinci Resolve **Studio**
project — including reading your edited timeline so Claude can write a script,
voiceover, or description that matches the actual cut.

## One-time setup

1. **Enable scripting in Resolve** (only needed once):
   `DaVinci Resolve` > `Preferences` > `System` > `General` >
   set **"External scripting using"** to **`Local`**. Click Save and restart Resolve.

2. The server is already registered with Claude (in `~/.claude.json` under
   `mcpServers` → `davinci-resolve`). **Fully quit and reopen the Claude app**
   so it loads the new server.

## Using it

Keep DaVinci Resolve **running with your project open**, then just ask Claude
in plain language. Examples:

- "Read my current Resolve timeline and write a voiceover script that matches the cut."
- "What clips are in the *Video1_4Processes* timeline and how long is each?"
- "Add markers on my timeline at each scene change with a one-line note."
- "Export the current timeline as an EDL to D:/exports/cut1.edl."
- "Summarize the pacing of my edit — how many cuts, average shot length."

Claude connects live to Resolve each time; nothing is cached.

## Tools exposed

| Tool | What it does |
|------|--------------|
| `resolve_get_project_info` | Project name, fps, resolution, list of all timelines |
| `resolve_get_timeline` | Full contents of a timeline: every clip in order with source file, in/out timecode, seconds, duration, plus markers |
| `resolve_get_media_pool` | All source clips by bin, with file paths and durations |
| `resolve_set_current_timeline` | Switch which timeline is open |
| `resolve_add_marker` | Drop a colored marker + note at a time on the timeline |
| `resolve_export_timeline` | Export a timeline (EDL/AAF/FCPXML/DRT/CSV/TXT) |
| `resolve_save_project` | Save the project |
| `resolve_run_script` | Escape hatch: run arbitrary Python against the Resolve API for anything above tools don't cover |

## Troubleshooting

- **"Could not connect to DaVinci Resolve"** — Resolve isn't running, or the
  scripting preference above isn't set to `Local`. Start Resolve, open a
  project, and confirm the setting.
- **Free vs Studio** — scripting only works in DaVinci Resolve **Studio**, not
  the free version.
- **Changed the Resolve install path?** — the server reads standard Windows
  paths; override with `RESOLVE_SCRIPT_API` / `RESOLVE_SCRIPT_LIB` env vars in
  the `env` block of the `davinci-resolve` entry in `~/.claude.json`.
