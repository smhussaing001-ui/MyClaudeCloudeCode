"""Connection + dependency self-test. Run first: python check_env.py"""
import shutil, sys

print("Python:", sys.version.split()[0], "| 64-bit:", sys.maxsize > 2**32)
try:
    import numpy; print("numpy:", numpy.__version__)
except ImportError:
    print("numpy: MISSING -> pip install numpy")
try:
    import requests; print("requests:", requests.__version__)
except ImportError:
    print("requests: MISSING -> pip install requests")
print("ffmpeg on PATH:", bool(shutil.which("ffmpeg")), "(needed for music step)")

try:
    from resolve_env import connect, fps_of
    resolve, project, tl = connect()
    print("\nResolve OK")
    print("  project :", project.GetName())
    print("  timeline:", tl.GetName(), "| fps:", fps_of(tl),
          "| end:", tl.GetEndFrame())
    print("  markers :", len(tl.GetMarkers() or {}))
    print("  video tracks:", tl.GetTrackCount("video"),
          "| audio tracks:", tl.GetTrackCount("audio"))
except SystemExit as e:
    print("\nResolve NOT connected:\n", e)
