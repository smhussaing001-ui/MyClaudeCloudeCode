#!/usr/bin/env python3
"""MCP server for DaVinci Resolve Studio.

Connects Claude to a running DaVinci Resolve instance through the official
scripting API (DaVinciResolveScript), so Claude can read the current project,
inspect timelines (clips, order, durations, markers), and perform edit
operations on request.

Requirements:
  - DaVinci Resolve Studio must be RUNNING with a project open.
  - Preferences > System > General > "External scripting using" = Local.
"""

import io
import json
import os
import sys
import contextlib
from typing import Any, Optional

from pydantic import Field
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# DaVinci Resolve scripting API bootstrap (Windows default install paths)
# ---------------------------------------------------------------------------
RESOLVE_SCRIPT_API = os.environ.get(
    "RESOLVE_SCRIPT_API",
    os.path.join(
        os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
        r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting",
    ),
)
RESOLVE_SCRIPT_LIB = os.environ.get(
    "RESOLVE_SCRIPT_LIB",
    r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll",
)
os.environ["RESOLVE_SCRIPT_API"] = RESOLVE_SCRIPT_API
os.environ["RESOLVE_SCRIPT_LIB"] = RESOLVE_SCRIPT_LIB
_modules_path = os.path.join(RESOLVE_SCRIPT_API, "Modules")
if _modules_path not in sys.path:
    sys.path.append(_modules_path)

mcp = FastMCP("davinci_resolve_mcp")

MARKER_COLORS = [
    "Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple", "Fuchsia",
    "Rose", "Lavender", "Sky", "Mint", "Lemon", "Sand", "Cocoa", "Cream",
]

NOT_RUNNING_MSG = (
    "Error: Could not connect to DaVinci Resolve. Make sure that:\n"
    "1. DaVinci Resolve Studio is running (launch it and open your project).\n"
    "2. In Resolve: Preferences > System > General > 'External scripting using' "
    "is set to 'Local'.\n"
    "Then retry this tool."
)


def _get_resolve():
    """Connect to the running Resolve instance. Raises RuntimeError with an
    actionable message if unavailable."""
    try:
        import DaVinciResolveScript as dvr  # noqa: N813
    except ImportError as e:
        raise RuntimeError(
            f"Error: Could not import DaVinciResolveScript ({e}). "
            f"Checked modules path: {_modules_path}. "
            "Verify DaVinci Resolve Studio is installed."
        )
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise RuntimeError(NOT_RUNNING_MSG)
    return resolve


def _get_project(resolve=None):
    resolve = resolve or _get_resolve()
    project = resolve.GetProjectManager().GetCurrentProject()
    if project is None:
        raise RuntimeError(
            "Error: Connected to Resolve, but no project is open. "
            "Open a project in DaVinci Resolve and retry."
        )
    return resolve, project


def _get_timeline(project, name: Optional[str] = None):
    """Return the current timeline, or the timeline matching `name`."""
    if name:
        for i in range(1, int(project.GetTimelineCount()) + 1):
            tl = project.GetTimelineByIndex(i)
            if tl and tl.GetName() == name:
                return tl
        names = [
            project.GetTimelineByIndex(i).GetName()
            for i in range(1, int(project.GetTimelineCount()) + 1)
        ]
        raise RuntimeError(
            f"Error: No timeline named '{name}'. Available timelines: {names}"
        )
    tl = project.GetCurrentTimeline()
    if tl is None:
        raise RuntimeError(
            "Error: Project has no open timeline. Open a timeline in the "
            "Edit page and retry, or pass a timeline name."
        )
    return tl


def _safe(obj: Any, method: str, *args, default=None):
    """Call an API method defensively — older Resolve versions may lack it."""
    try:
        fn = getattr(obj, method, None)
        if fn is None:
            return default
        result = fn(*args)
        return default if result is None else result
    except Exception:
        return default


def _timeline_fps(timeline) -> float:
    try:
        return float(timeline.GetSetting("timelineFrameRate"))
    except Exception:
        return 24.0


def _frames_to_tc(frames: int, fps: float) -> str:
    """Convert a frame count to HH:MM:SS:FF timecode (non-drop)."""
    fps_i = max(1, round(fps))
    total_seconds, ff = divmod(int(frames), fps_i)
    hh, rem = divmod(total_seconds, 3600)
    mm, ss = divmod(rem, 60)
    return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def _seconds(frames: int, fps: float) -> float:
    return round(int(frames) / fps, 3) if fps else 0.0


def _clip_info(item, fps: float, timeline_start: int) -> dict:
    """Extract the useful fields from a timeline item."""
    start = int(_safe(item, "GetStart", default=0))
    end = int(_safe(item, "GetEnd", default=0))
    duration = int(_safe(item, "GetDuration", default=end - start))
    rel_start = start - timeline_start
    rel_end = end - timeline_start

    info = {
        "name": _safe(item, "GetName", default=""),
        "timeline_in": _frames_to_tc(rel_start, fps),
        "timeline_out": _frames_to_tc(rel_end, fps),
        "start_seconds": _seconds(rel_start, fps),
        "end_seconds": _seconds(rel_end, fps),
        "duration_seconds": _seconds(duration, fps),
    }

    mpi = _safe(item, "GetMediaPoolItem")
    if mpi is not None:
        file_path = _safe(mpi, "GetClipProperty", "File Path", default="")
        if file_path:
            info["source_file"] = file_path
        source_in = _safe(item, "GetLeftOffset")
        if source_in is not None:
            info["source_in_seconds"] = _seconds(int(source_in), fps)

    enabled = _safe(item, "GetClipEnabled")
    if enabled is False:
        info["enabled"] = False

    return info


def _markers_list(obj, fps: float) -> list:
    """Markers of a timeline (or clip) as a sorted list."""
    markers = _safe(obj, "GetMarkers", default={}) or {}
    out = []
    for frame_id, m in sorted(markers.items(), key=lambda kv: int(kv[0])):
        out.append({
            "at_seconds": _seconds(int(frame_id), fps),
            "timecode": _frames_to_tc(int(frame_id), fps),
            "color": m.get("color", ""),
            "name": m.get("name", ""),
            "note": m.get("note", ""),
            "duration_frames": m.get("duration", 0),
        })
    return out


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    name="resolve_get_project_info",
    annotations={
        "title": "Get Resolve Project Info",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def resolve_get_project_info() -> str:
    """Get an overview of the currently open DaVinci Resolve project.

    Returns project name, frame rate, resolution, the list of all timelines,
    and which timeline is currently open. Call this first to orient yourself
    before reading timeline contents.

    Returns:
        str: JSON with {project_name, frame_rate, resolution, current_timeline,
             timelines: [{index, name, duration_seconds, video_tracks,
             audio_tracks}]}, or an "Error: ..." message.
    """
    try:
        _, project = _get_project()
        current = project.GetCurrentTimeline()
        timelines = []
        for i in range(1, int(project.GetTimelineCount()) + 1):
            tl = project.GetTimelineByIndex(i)
            if tl is None:
                continue
            fps = _timeline_fps(tl)
            dur = int(_safe(tl, "GetEndFrame", default=0)) - int(
                _safe(tl, "GetStartFrame", default=0))
            timelines.append({
                "index": i,
                "name": tl.GetName(),
                "duration_seconds": _seconds(dur, fps),
                "frame_rate": fps,
                "video_tracks": int(_safe(tl, "GetTrackCount", "video", default=0)),
                "audio_tracks": int(_safe(tl, "GetTrackCount", "audio", default=0)),
            })
        return _json({
            "project_name": project.GetName(),
            "frame_rate": _safe(project, "GetSetting", "timelineFrameRate", default=""),
            "resolution": (
                f"{_safe(project, 'GetSetting', 'timelineResolutionWidth', default='?')}"
                f"x{_safe(project, 'GetSetting', 'timelineResolutionHeight', default='?')}"
            ),
            "current_timeline": current.GetName() if current else None,
            "timeline_count": len(timelines),
            "timelines": timelines,
        })
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_get_timeline",
    annotations={
        "title": "Read Timeline Contents",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def resolve_get_timeline(
    timeline_name: Optional[str] = Field(
        default=None,
        description="Name of the timeline to read. Omit to read the currently open timeline.",
    ),
    include_audio: bool = Field(
        default=True, description="Include audio tracks in the output."
    ),
) -> str:
    """Read the full edited contents of a timeline, in playback order.

    This is the main tool for understanding an edit: it returns every clip on
    every track with its name, source file, position on the timeline (timecode
    and seconds from timeline start), duration, and all timeline markers.
    Use it when asked to write a script/voiceover/description that matches the
    edit, to analyze pacing, or before making changes.

    Args:
        timeline_name: Timeline to read (default: the currently open one).
        include_audio: Whether audio tracks are included (default true).

    Returns:
        str: JSON with {timeline, frame_rate, duration_seconds,
             video_tracks: [{track, track_name, clips: [...]}],
             audio_tracks: [...], markers: [...]}. Clips carry
             timeline_in/out timecodes, start/end/duration in seconds, and
             source_file paths. Or an "Error: ..." message.
    """
    try:
        _, project = _get_project()
        tl = _get_timeline(project, timeline_name)
        fps = _timeline_fps(tl)
        tl_start = int(_safe(tl, "GetStartFrame", default=0))
        tl_end = int(_safe(tl, "GetEndFrame", default=0))

        def read_tracks(kind: str) -> list:
            tracks = []
            for t in range(1, int(_safe(tl, "GetTrackCount", kind, default=0)) + 1):
                items = _safe(tl, "GetItemListInTrack", kind, t, default=[]) or []
                clips = [_clip_info(item, fps, tl_start) for item in items]
                if clips:
                    tracks.append({
                        "track": t,
                        "track_name": _safe(tl, "GetTrackName", kind, t, default=f"{kind} {t}"),
                        "clip_count": len(clips),
                        "clips": clips,
                    })
            return tracks

        data = {
            "timeline": tl.GetName(),
            "frame_rate": fps,
            "duration_seconds": _seconds(tl_end - tl_start, fps),
            "start_timecode": _safe(tl, "GetStartTimecode", default=""),
            "video_tracks": read_tracks("video"),
            "markers": _markers_list(tl, fps),
        }
        if include_audio:
            data["audio_tracks"] = read_tracks("audio")
        return _json(data)
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_get_media_pool",
    annotations={
        "title": "List Media Pool Contents",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def resolve_get_media_pool() -> str:
    """List all clips in the project's media pool, organized by bin/folder.

    Useful for seeing what source footage exists beyond what is already cut
    into the timeline, or for finding a clip's file path and duration.

    Returns:
        str: JSON with {folders: [{name, clips: [{name, duration, fps,
             resolution, file_path}]}]}, or an "Error: ..." message.
    """
    try:
        _, project = _get_project()
        media_pool = project.GetMediaPool()
        root = media_pool.GetRootFolder()

        def read_folder(folder, path: str) -> list:
            entries = []
            clips = []
            for clip in _safe(folder, "GetClipList", default=[]) or []:
                props = _safe(clip, "GetClipProperty", default={}) or {}
                clips.append({
                    "name": props.get("Clip Name") or _safe(clip, "GetName", default=""),
                    "duration": props.get("Duration", ""),
                    "fps": props.get("FPS", ""),
                    "resolution": props.get("Resolution", ""),
                    "type": props.get("Type", ""),
                    "file_path": props.get("File Path", ""),
                })
            entries.append({"folder": path, "clip_count": len(clips), "clips": clips})
            for sub in _safe(folder, "GetSubFolderList", default=[]) or []:
                sub_name = _safe(sub, "GetName", default="?")
                entries.extend(read_folder(sub, f"{path}/{sub_name}"))
            return entries

        return _json({"folders": read_folder(root, root.GetName() or "Master")})
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_set_current_timeline",
    annotations={
        "title": "Switch Current Timeline",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def resolve_set_current_timeline(
    timeline_name: str = Field(..., description="Exact name of the timeline to open.", min_length=1),
) -> str:
    """Switch which timeline is currently open in DaVinci Resolve.

    Args:
        timeline_name: Exact timeline name (see resolve_get_project_info for the list).

    Returns:
        str: Confirmation message, or "Error: ..." with the available names.
    """
    try:
        _, project = _get_project()
        tl = _get_timeline(project, timeline_name)
        if project.SetCurrentTimeline(tl):
            return f"Current timeline is now '{timeline_name}'."
        return f"Error: Resolve refused to switch to '{timeline_name}'."
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_add_marker",
    annotations={
        "title": "Add Timeline Marker",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def resolve_add_marker(
    at_seconds: float = Field(..., description="Position in seconds from the start of the timeline.", ge=0),
    name: str = Field(default="", description="Marker title."),
    note: str = Field(default="", description="Longer note text shown in the marker."),
    color: str = Field(default="Blue", description=f"Marker color, one of: {', '.join(MARKER_COLORS)}."),
    timeline_name: Optional[str] = Field(default=None, description="Timeline to mark (default: current)."),
) -> str:
    """Add a marker to a timeline at a given position.

    Useful for annotating the edit — e.g. dropping script cues, chapter
    points, or review notes directly onto the timeline where the editor can
    see them.

    Args:
        at_seconds: Seconds from timeline start (matches the *_seconds values
            returned by resolve_get_timeline).
        name: Marker title.
        note: Marker note body.
        color: One of the standard Resolve marker colors (default Blue).
        timeline_name: Target timeline (default: currently open one).

    Returns:
        str: Confirmation with the frame/timecode used, or "Error: ...".
    """
    try:
        if color not in MARKER_COLORS:
            return f"Error: '{color}' is not a valid marker color. Use one of: {', '.join(MARKER_COLORS)}"
        _, project = _get_project()
        tl = _get_timeline(project, timeline_name)
        fps = _timeline_fps(tl)
        frame = int(round(at_seconds * fps))
        if tl.AddMarker(frame, color, name or "Marker", note, 1, ""):
            return (f"Added {color} marker '{name or 'Marker'}' at "
                    f"{_frames_to_tc(frame, fps)} ({at_seconds}s) on '{tl.GetName()}'.")
        return ("Error: Resolve rejected the marker. A marker may already exist at "
                f"frame {frame}, or the position is outside the timeline.")
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_export_timeline",
    annotations={
        "title": "Export Timeline File",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def resolve_export_timeline(
    file_path: str = Field(..., description="Absolute output path including extension, e.g. 'D:/exports/cut1.edl'.", min_length=3),
    format: str = Field(default="edl", description="Export format: 'edl', 'aaf', 'fcpxml', 'drt', 'csv', or 'txt'."),
    timeline_name: Optional[str] = Field(default=None, description="Timeline to export (default: current)."),
) -> str:
    """Export a timeline to an interchange file (EDL, AAF, FCPXML, DRT, CSV, TXT).

    Args:
        file_path: Where to write the exported file.
        format: One of edl, aaf, fcpxml, drt, csv, txt.
        timeline_name: Timeline to export (default: currently open one).

    Returns:
        str: Confirmation with the written path, or "Error: ...".
    """
    try:
        resolve, project = _get_project()
        tl = _get_timeline(project, timeline_name)
        fmt = format.lower().strip(".")
        format_map = {
            "edl": (getattr(resolve, "EXPORT_EDL", None), getattr(resolve, "EXPORT_NONE", None)),
            "aaf": (getattr(resolve, "EXPORT_AAF", None), getattr(resolve, "EXPORT_AAF_NEW", None)),
            "fcpxml": (getattr(resolve, "EXPORT_FCPXML_1_8", None), getattr(resolve, "EXPORT_NONE", None)),
            "drt": (getattr(resolve, "EXPORT_DRT", None), getattr(resolve, "EXPORT_NONE", None)),
            "csv": (getattr(resolve, "EXPORT_TEXT_CSV", None), getattr(resolve, "EXPORT_NONE", None)),
            "txt": (getattr(resolve, "EXPORT_TEXT_TAB", None), getattr(resolve, "EXPORT_NONE", None)),
        }
        if fmt not in format_map:
            return f"Error: Unknown format '{format}'. Use one of: {', '.join(format_map)}"
        export_type, export_subtype = format_map[fmt]
        if export_type is None:
            return f"Error: This Resolve version does not expose the '{fmt}' export constant."
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        ok = (tl.Export(file_path, export_type, export_subtype)
              if export_subtype is not None else tl.Export(file_path, export_type))
        if ok:
            return f"Exported '{tl.GetName()}' as {fmt.upper()} to {file_path}"
        return "Error: Resolve reported the export failed. Check the path is writable."
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_save_project",
    annotations={
        "title": "Save Resolve Project",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
def resolve_save_project() -> str:
    """Save the currently open DaVinci Resolve project.

    Returns:
        str: Confirmation message, or "Error: ...".
    """
    try:
        resolve, project = _get_project()
        if resolve.GetProjectManager().SaveProject():
            return f"Project '{project.GetName()}' saved."
        return "Error: Resolve reported the save failed."
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Unexpected failure: {type(e).__name__}: {e}"


@mcp.tool(
    name="resolve_run_script",
    annotations={
        "title": "Run Python in Resolve",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
def resolve_run_script(
    code: str = Field(..., description=(
        "Python code to execute against the Resolve scripting API. Pre-bound "
        "variables: resolve, project_manager, project, media_pool, timeline "
        "(current timeline or None). Set a variable named `result` or print() "
        "to return output."
    ), min_length=1),
) -> str:
    """Run arbitrary Python against the DaVinci Resolve scripting API.

    Escape hatch for anything not covered by the dedicated tools (creating
    timelines, editing clip properties, color page operations, render jobs,
    Fusion, etc.). The full scripting API is documented in Resolve under
    Help > Documentation > Developer.

    The code runs with these variables already bound:
        resolve, project_manager, project, media_pool, timeline

    Anything printed, plus the value of a variable named `result` if set, is
    returned. This can modify the user's project — prefer the dedicated
    read-only tools when only reading.

    Args:
        code: Python source to execute.

    Returns:
        str: Captured stdout and/or the `result` value, or "Error: ..." with
             the exception details.
    """
    try:
        resolve, project = _get_project()
        env = {
            "resolve": resolve,
            "project_manager": resolve.GetProjectManager(),
            "project": project,
            "media_pool": project.GetMediaPool(),
            "timeline": project.GetCurrentTimeline(),
        }
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exec(code, env)  # noqa: S102 — intentional: user-directed automation
        parts = []
        if stdout.getvalue().strip():
            parts.append(stdout.getvalue().strip())
        if "result" in env and env["result"] is not None:
            parts.append(_json(env["result"]) if isinstance(env["result"], (dict, list))
                         else str(env["result"]))
        return "\n".join(parts) if parts else "Script ran successfully (no output)."
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Error: Script raised {type(e).__name__}: {e}"


if __name__ == "__main__":
    mcp.run()
