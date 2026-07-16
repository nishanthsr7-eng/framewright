"""Framewright bridge: small helpers for DaVinci Resolve scripts.

LLM-generated scripts import this so they don't re-implement the Resolve API
plumbing. Works inside Resolve (Workspace > Scripts, Console) and from a
terminal (Studio, external scripting enabled).

    import sys; sys.path.insert(0, r"<repo>/resolve/bridge")
    import framewright_bridge as fw

    resolve = fw.connect(globals().get("resolve"))
    report = fw.build_from_plan(resolve, fw.load_plan("examples/edit_plan.example.json"))

No hardcoded paths: the scripting module location comes from the
RESOLVE_SCRIPT_API / RESOLVE_SCRIPT_LIB environment variables, or the
standard install location for the OS.
"""
from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

# Standard Resolve install locations: (scripting API folder, fusionscript library).
_DEFAULTS = {
    "Windows": (
        os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                     r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting"),
        r"C:\Program Files\Blackmagic Design\DaVinci Resolve\fusionscript.dll",
    ),
    "Darwin": (
        "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting",
        "/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so",
    ),
    "Linux": (
        "/opt/resolve/Developer/Scripting",
        "/opt/resolve/libs/Fusion/fusionscript.so",
    ),
}

MARKER_COLORS = {
    "Blue", "Cyan", "Green", "Yellow", "Red", "Pink", "Purple", "Fuchsia",
    "Rose", "Lavender", "Sky", "Mint", "Lemon", "Sand", "Cocoa", "Cream",
}


class BridgeError(RuntimeError):
    pass


# ── connection ────────────────────────────────────────────────────────────────

def connect(resolve=None):
    """Return the Resolve object. Pass the `resolve` global when running inside Resolve."""
    if resolve is not None:
        return resolve
    api, lib = _DEFAULTS.get(platform.system(), ("", ""))
    os.environ.setdefault("RESOLVE_SCRIPT_API", api)
    os.environ.setdefault("RESOLVE_SCRIPT_LIB", lib)
    modules = os.path.join(os.environ["RESOLVE_SCRIPT_API"], "Modules")
    if modules not in sys.path:
        sys.path.insert(0, modules)
    try:
        import DaVinciResolveScript as dvr  # type: ignore
    except ImportError as e:
        raise BridgeError(
            "DaVinciResolveScript not found. Set RESOLVE_SCRIPT_API and RESOLVE_SCRIPT_LIB "
            "to your Resolve install, or run the script from inside Resolve."
        ) from e
    resolve = dvr.scriptapp("Resolve")
    if resolve is None:
        raise BridgeError(
            "Cannot connect to DaVinci Resolve. Start Resolve and set "
            "Preferences > System > General > External scripting using = Local."
        )
    return resolve


def get_project(resolve, name: str | None = None):
    """Current project, or a new one named `name` if none is open."""
    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    if project is None and name:
        project = pm.CreateProject(name)
    if project is None:
        raise BridgeError("No project open. Open or create a project in Resolve first.")
    return project


def set_format(project, width: int, height: int, fps: float) -> bool:
    """Set timeline resolution and frame rate. Call before creating the timeline."""
    ok = project.SetSetting("timelineResolutionWidth", str(int(width)))
    ok = project.SetSetting("timelineResolutionHeight", str(int(height))) and ok
    fps_str = str(int(fps)) if float(fps).is_integer() else str(fps)
    return project.SetSetting("timelineFrameRate", fps_str) and ok


# ── time ──────────────────────────────────────────────────────────────────────

def to_frames(seconds: float, fps: float) -> int:
    return int(round(seconds * fps))


def to_srt_time(seconds: float) -> str:
    ms_total = int(round(seconds * 1000))
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── media pool ────────────────────────────────────────────────────────────────

def get_bin(media_pool, path: str):
    """Get or create a bin by slash path, e.g. "Framewright/Video"."""
    folder = media_pool.GetRootFolder()
    for name in [p for p in path.split("/") if p]:
        sub = next((f for f in (folder.GetSubFolderList() or []) if f.GetName() == name), None)
        folder = sub or media_pool.AddSubFolder(folder, name)
        if folder is None:
            raise BridgeError(f"Could not create bin '{name}'.")
    return folder


def find_clip(media_pool, file_path: str):
    """Find a media pool item by file path (or file name), searching every bin."""
    target = os.path.normcase(os.path.abspath(file_path))
    name = os.path.basename(file_path)
    by_name = None
    stack = [media_pool.GetRootFolder()]
    while stack:
        folder = stack.pop()
        for clip in folder.GetClipList() or []:
            fp = clip.GetClipProperty("File Path") or ""
            if fp and os.path.normcase(os.path.abspath(fp)) == target:
                return clip
            if by_name is None and clip.GetName() == name:
                by_name = clip
        stack.extend(folder.GetSubFolderList() or [])
    return by_name


def import_media(media_pool, paths, bin_path: str | None = None) -> dict:
    """Import files (reusing ones already in the pool). Returns {abs path: item or None}."""
    if bin_path:
        media_pool.SetCurrentFolder(get_bin(media_pool, bin_path))
    result, to_import = {}, []
    for p in dict.fromkeys(os.path.abspath(p) for p in paths):
        existing = find_clip(media_pool, p)
        if existing is not None:
            result[p] = existing
        elif os.path.isfile(p):
            to_import.append(p)
        else:
            result[p] = None
    imported = (media_pool.ImportMedia(to_import) or []) if to_import else []
    by_path = {os.path.normcase(os.path.abspath(i.GetClipProperty("File Path") or "")): i for i in imported}
    for p in to_import:
        result[p] = by_path.get(os.path.normcase(p)) or find_clip(media_pool, p)
    return result


def clip_fps(item, fallback: float) -> float:
    try:
        fps = float(item.GetClipProperty("FPS") or 0)
    except (TypeError, ValueError):
        fps = 0.0
    return fps if fps > 0 else fallback


# ── timeline ──────────────────────────────────────────────────────────────────

def create_timeline(project, media_pool, name: str, video_tracks: int = 1):
    """Create a timeline with a unique name (never deletes existing ones) and make it current."""
    taken = {project.GetTimelineByIndex(i).GetName() for i in range(1, project.GetTimelineCount() + 1)}
    final, n = name, 2
    while final in taken:
        final, n = f"{name}_{n}", n + 1
    timeline = media_pool.CreateEmptyTimeline(final)
    if timeline is None:
        raise BridgeError(f"Could not create timeline '{final}'.")
    project.SetCurrentTimeline(timeline)
    while timeline.GetTrackCount("video") < video_tracks:
        timeline.AddTrack("video")
    return timeline


def place_clip(media_pool, timeline, item, in_s: float, out_s: float, at_s: float,
               fps: float, track: int = 1, media_type: int | None = 1):
    """Place item[in_s:out_s] at timeline time at_s. media_type: 1 video, 2 audio, None both."""
    src_fps = clip_fps(item, fps)
    info = {
        "mediaPoolItem": item,
        "startFrame": to_frames(in_s, src_fps),
        "endFrame": max(to_frames(in_s, src_fps), to_frames(out_s, src_fps) - 1),
        "trackIndex": track,
        "recordFrame": timeline.GetStartFrame() + to_frames(at_s, fps),
    }
    if media_type is not None:
        info["mediaType"] = media_type
    placed = media_pool.AppendToTimeline([info]) or []
    return placed[0] if placed else None


def set_speed(timeline_item, speed: float) -> bool:
    """Best effort: not every Resolve version exposes retime to scripts."""
    try:
        return bool(timeline_item.SetProperty("Speed", speed * 100.0))
    except Exception:
        return False


def add_marker(timeline, at_s: float, fps: float, color: str = "Blue", name: str = "",
               note: str = "", duration_s: float = 0.0) -> bool:
    if color not in MARKER_COLORS:
        color = "Blue"
    frame = to_frames(at_s, fps)
    duration = max(1, to_frames(duration_s, fps))
    # Resolve refuses two markers on one frame; nudge forward until free.
    for offset in range(10):
        if timeline.AddMarker(frame + offset, color, name, note, duration):
            return True
    return False


def write_srt(segments, path) -> Path:
    """segments: [{start, end, text}] (e.g. transcribe_audio output)."""
    lines = []
    for i, seg in enumerate(segments, 1):
        lines += [str(i), f"{to_srt_time(seg['start'])} --> {to_srt_time(seg['end'])}",
                  str(seg["text"]).strip(), ""]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── edit plan ─────────────────────────────────────────────────────────────────

def load_plan(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_from_plan(resolve, plan: dict, base_dir=".", log=print) -> dict:
    """Build a timeline from an edit plan (docs/edit-plan.md). Never stops on one bad item."""
    base = Path(base_dir)
    absp = lambda p: str(p if os.path.isabs(p) else (base / p).resolve())
    proj_cfg = plan.get("project", {})
    fps = float(proj_cfg.get("fps", 24))
    report = {"clips_placed": 0, "markers": 0, "skipped": []}

    project = get_project(resolve, proj_cfg.get("name", "framewright"))
    set_format(project, proj_cfg.get("width", 1920), proj_cfg.get("height", 1080), fps)
    mp = project.GetMediaPool()

    clips = plan.get("clips", [])
    music = plan.get("music")
    files = [absp(c["file"]) for c in clips] + ([absp(music["file"])] if music else [])
    items = import_media(mp, files, "Framewright")
    for p, it in items.items():
        if it is None:
            report["skipped"].append(f"missing file: {p}")

    tracks = max([c.get("track", 1) for c in clips] + [t.get("track", 2) for t in plan.get("titles", [])] + [1])
    timeline = create_timeline(project, mp, proj_cfg.get("name", "framewright"), tracks)

    for c in sorted(clips, key=lambda c: c.get("at", 0)):
        item = items.get(absp(c["file"]))
        if item is None:
            continue
        speed = float(c.get("speed", 1.0))
        ti = place_clip(mp, timeline, item, c["in"], c["out"], c["at"], fps, c.get("track", 1))
        if ti is None:
            report["skipped"].append(f"could not place {c['file']} at {c['at']}s")
            continue
        report["clips_placed"] += 1
        notes = [("Cyan", f"FX: {fx}") for fx in c.get("effects", [])]
        tr = c.get("transition_in")
        if tr:
            notes.append(("Pink", f"TRANSITION: {tr['type']} {tr.get('frames', '')}f".strip()))
        if speed != 1.0 and not set_speed(ti, speed):
            notes.append(("Purple", f"SPEED: {speed}x"))
        for color, name in notes:
            report["markers"] += add_marker(timeline, c["at"], fps, color, name)

    if music and items.get(absp(music["file"])) is not None:
        it = items[absp(music["file"])]
        frames = int(it.GetClipProperty("Frames") or 0)
        end_s = frames / clip_fps(it, fps) if frames else 3600.0
        if place_clip(mp, timeline, it, music.get("start", 0.0), end_s, 0.0, fps, 1, 2) is None:
            report["skipped"].append("could not place music")

    for t in plan.get("titles", []):
        timeline.SetCurrentTimecode(_timecode(timeline.GetStartFrame() + to_frames(t["at"], fps), fps))
        ok = None
        try:
            ok = timeline.InsertFusionTitleIntoTimeline(t.get("template", "Text+"))
        except Exception:
            pass
        if not ok:
            report["markers"] += add_marker(timeline, t["at"], fps, "Yellow", f"TITLE: {t['text']}",
                                            duration_s=t.get("duration", 0))

    for m in plan.get("markers", []):
        report["markers"] += add_marker(timeline, m["at"], fps, m.get("color", "Blue"),
                                        m.get("name", ""), m.get("note", ""))

    log(f"Placed {report['clips_placed']}/{len(clips)} clips, {report['markers']} markers.")
    for s in report["skipped"]:
        log(f"  skipped: {s}")
    return report


def _timecode(frame: int, fps: float) -> str:
    rate = int(round(fps))
    f = frame % rate
    s = frame // rate
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{f:02d}"
