"""
resolve_env.py — cross-platform DaVinci Resolve scripting connection.

Import this at the top of every pipeline script:

    from resolve_env import connect
    resolve, project, timeline = connect()

Prereqs (do these ONCE on the machine):
  * DaVinci Resolve *Studio* running with a project + timeline open.
  * Preferences > System > General > External scripting using = **Local**.
  * Python 3.10+  (same bitness as Resolve, i.e. 64-bit).

The Resolve scripting module (DaVinciResolveScript) and native library live in
different places per OS. This file finds them automatically. If it still fails,
set these environment variables to match your install and re-run:

  Windows:
    RESOLVE_SCRIPT_API = C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting
    RESOLVE_SCRIPT_LIB = C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll
  macOS:
    RESOLVE_SCRIPT_API = /Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting
    RESOLVE_SCRIPT_LIB = /Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so
  Linux:
    RESOLVE_SCRIPT_API = /opt/resolve/Developer/Scripting
    RESOLVE_SCRIPT_LIB = /opt/resolve/libs/Fusion/fusionscript.so
"""
import os
import sys


def _default_paths():
    pd = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
    pf = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    if sys.platform.startswith("win"):
        api = os.path.join(pd, "Blackmagic Design", "DaVinci Resolve",
                           "Support", "Developer", "Scripting")
        lib = os.path.join(pf, "Blackmagic Design", "DaVinci Resolve",
                           "fusionscript.dll")
    elif sys.platform == "darwin":
        api = ("/Library/Application Support/Blackmagic Design/"
               "DaVinci Resolve/Developer/Scripting")
        lib = ("/Applications/DaVinci Resolve/DaVinci Resolve.app/"
               "Contents/Libraries/Fusion/fusionscript.so")
    else:
        api = "/opt/resolve/Developer/Scripting"
        lib = "/opt/resolve/libs/Fusion/fusionscript.so"
    return api, lib


def connect():
    """Return (resolve, project, current_timeline). Raises with a clear message."""
    api, lib = _default_paths()
    os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    mod = os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules")
    if mod not in sys.path:
        sys.path.append(mod)
    try:
        import DaVinciResolveScript as dvr
    except ImportError as e:
        raise SystemExit(
            "Could not import DaVinciResolveScript.\n"
            f"Looked in: {mod}\n"
            "Fix: set RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB env vars (see "
            "resolve_env.py header) and make sure Python is 64-bit.\n"
            f"Original error: {e}")
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise SystemExit(
            "Resolve returned None. Is Resolve *running*, and is "
            "Preferences > System > General > External scripting = Local?")
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    if project is None:
        raise SystemExit("No project open in Resolve.")
    timeline = project.GetCurrentTimeline()
    if timeline is None:
        raise SystemExit("No timeline open in Resolve.")
    return resolve, project, timeline


# ---- tiny shared helpers every script needs ----

def fps_of(timeline):
    try:
        return float(timeline.GetSetting("timelineFrameRate"))
    except (TypeError, ValueError):
        return 24.0


def frames_to_tc(frame, fps):
    fi = int(round(fps)); f = int(frame)
    return f"{f//3600//fi:02d}:{(f//fi)//60%60:02d}:{(f//fi)%60:02d}:{f%fi:02d}"


def goto(timeline, frame, fps, settle=0.6, tries=6):
    """Move playhead and CONFIRM it landed. Returns True/False.
    Without the read-back, GrabStill/thumbnail can capture a STALE frame."""
    import time
    tc = frames_to_tc(frame, fps)
    for _ in range(tries):
        timeline.SetCurrentTimecode(tc)
        time.sleep(settle)
        if timeline.GetCurrentTimecode() == tc:
            return True
    return False


def clip_frames(media_pool_item, fps):
    """Audio clips have NO 'Frames' property — only 'Duration' as HH:MM:SS:FF.
    Video clips DO have 'Frames'. This handles both."""
    fr = media_pool_item.GetClipProperty("Frames")
    if fr not in (None, ""):
        return int(fr)
    d = media_pool_item.GetClipProperty("Duration")   # 'HH:MM:SS:FF'
    h, m, s, f = (int(x) for x in d.split(":"))
    return ((h * 60 + m) * 60 + s) * int(round(fps)) + f


def save(project_manager_or_project):
    """SaveProject lives on ProjectManager, NOT Project. Accepts either."""
    obj = project_manager_or_project
    if hasattr(obj, "SaveProject"):
        return obj.SaveProject()
    return obj.GetProjectManager().SaveProject()  # if a Resolve obj slipped in
