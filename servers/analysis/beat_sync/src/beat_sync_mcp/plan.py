"""Edit plan (docs/edit-plan.md): draft one from music + clips, and validate one before Resolve runs it."""

import json
import os
import subprocess
from typing import Any

from framewright_core import output_root as _get_output_root

from beat_sync_mcp.beat_sync import detect_beats

PLAN_VERSION = "0.1"


def _repo_root():
    return os.path.dirname(_get_output_root())


def _resolve_path(path, base_dir):
    return path if os.path.isabs(path) else os.path.join(base_dir, path)


def _media_info(path):
    """Duration and first-video-stream fps (None for audio-only). Raises FileNotFoundError."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {path}")
    data = json.loads(out.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    fps = None
    if v:
        num, den = (v.get("r_frame_rate", "0/1").split("/") + ["1"])[:2]
        fps = float(num) / float(den) if float(den) else None
    return {
        "duration": float(data["format"].get("duration") or 0.0),
        "fps": fps,
        "width": int(v["width"]) if v else None,
        "height": int(v["height"]) if v else None,
    }


def build_edit_plan(
    clip_paths: list[str],
    music_path: str,
    output_path: str | None = None,
    beats_per_cut: int = 2,
    max_duration: float | None = None,
    project_name: str | None = None,
) -> dict:
    """Beat-grid + one clip per cut, cycling through clips and walking forward through each."""
    music = _media_info(music_path)
    infos = [_media_info(p) for p in clip_paths]
    beats = detect_beats(music_path)
    grid = beats["beat_times"]
    if len(grid) < 2:
        raise RuntimeError("Not enough beats found in the music; try a track with a clearer rhythm")

    end = min(float(max_duration), music["duration"]) if max_duration else music["duration"]
    cuts = [t for t in grid[::beats_per_cut] if t < end]
    if not cuts or cuts[0] > 0.01:
        cuts = [0.0] + cuts
    cuts.append(end)

    first = infos[0]
    fps = round(first["fps"] or 30.0, 3)
    cursor = [0.0] * len(clip_paths)  # next unused source second per clip
    clips = []
    for i, (at, nxt) in enumerate(zip(cuts, cuts[1:], strict=False)):
        length = round(nxt - at, 3)
        if length < 0.05:
            continue
        k = i % len(clip_paths)
        if cursor[k] + length > infos[k]["duration"]:
            cursor[k] = 0.0  # wrap to the start of a short clip
        if length > infos[k]["duration"]:
            length = round(infos[k]["duration"], 3)
        clips.append(
            {
                "file": clip_paths[k],
                "in": round(cursor[k], 3),
                "out": round(cursor[k] + length, 3),
                "track": 1,
                "at": round(at, 3),
                "speed": 1.0,
            }
        )
        cursor[k] += length

    name = project_name or os.path.splitext(os.path.basename(music_path))[0] + "_edit"
    plan = {
        "version": PLAN_VERSION,
        "project": {"name": name, "width": first["width"] or 1920, "height": first["height"] or 1080, "fps": fps},
        "music": {"file": music_path, "start": 0.0, "gain_db": 0},
        "beat_grid": {"bpm": beats["tempo"], "beats": grid, "downbeats": [], "sections": []},
        "clips": clips,
        "titles": [],
        "markers": [],
        "notes": "Draft from build_edit_plan. Add downbeats/sections from audio_analyzer, titles and "
        "transitions, then run validate_plan.",
    }
    if output_path is None:
        out_dir = os.path.join(_get_output_root(), os.path.splitext(os.path.basename(music_path))[0])
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, "edit_plan.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    write_plan_lua(plan, output_path)
    return {
        "output_path": output_path,
        "clip_count": len(clips),
        "bpm": beats["tempo"],
        "duration": round(end, 3),
        "fps": fps,
    }


def _lua(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v)  # JSON string escapes are valid Lua
    if isinstance(v, dict):
        return "{" + ", ".join(f"[{json.dumps(str(k))}] = {_lua(x)}" for k, x in v.items()) + "}"
    if isinstance(v, (list, tuple)):
        return "{" + ", ".join(_lua(x) for x in v) + "}"
    return "nil"


def write_plan_lua(plan: dict, plan_path: str, base_dir: str | None = None) -> str:
    """Write output/framewright_plan.lua for resolve/scripts/Edit/Framewright/framewright_build_plan.lua.
    Resolve Free may not find Python, but always runs Lua; paths are made absolute here."""
    base_dir = base_dir or _repo_root()
    absp = lambda p: os.path.abspath(_resolve_path(p, base_dir)).replace("\\", "/")
    out: dict = dict(plan, source=os.path.abspath(plan_path).replace("\\", "/"))
    out["clips"] = [dict(c, file=absp(c["file"])) for c in plan.get("clips") or []]
    if plan.get("music"):
        out["music"] = dict(plan["music"], file=absp(plan["music"]["file"]))
    out.pop("beat_grid", None)
    path = os.path.join(_get_output_root(), "framewright_plan.lua")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("return " + _lua(out) + "\n")  # loaded with dofile (Resolve's Lua has no io)
    return path


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate_plan(
    plan_path: str,
    base_dir: str | None = None,
    beat_tolerance_frames: int = 1,
    require_beats: bool = True,
) -> dict:
    """Return errors (Resolve would fail or the edit is wrong) and warnings (probably unintended)."""
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    base_dir = base_dir or _repo_root()
    errors, warnings = [], []

    proj = plan.get("project") or {}
    fps: Any = proj.get("fps")
    if not _num(fps) or fps <= 0:
        errors.append("project.fps must be a positive number")
        fps = 24.0
    fps = float(fps)
    for key in ("width", "height"):
        if not (isinstance(proj.get(key), int) and proj[key] > 0):
            errors.append(f"project.{key} must be a positive integer")
    if plan.get("version") != PLAN_VERSION:
        warnings.append(f"version is {plan.get('version')!r}; this validator knows {PLAN_VERSION!r}")

    media_cache = {}

    def info(path, where):
        full = _resolve_path(path, base_dir)
        if full not in media_cache:
            try:
                media_cache[full] = _media_info(full)
            except FileNotFoundError:
                media_cache[full] = None
                errors.append(f"{where}: file not found: {path}")
            except RuntimeError as e:
                media_cache[full] = None
                errors.append(f"{where}: {e}")
        return media_cache[full]

    music = plan.get("music")
    if music:
        m = info(music.get("file", ""), "music")
        if m and _num(music.get("start")) and music["start"] >= m["duration"]:
            errors.append("music.start is past the end of the music file")

    beats = sorted((plan.get("beat_grid") or {}).get("beats") or [])
    tol = beat_tolerance_frames / fps
    if require_beats and not beats:
        warnings.append("beat_grid.beats is empty, so cuts can't be checked against beats")

    def off_beat(t):
        if not beats:
            return None
        nearest = min(beats, key=lambda b: abs(b - t))
        return None if abs(nearest - t) <= tol or t < tol else round(t - nearest, 3)

    timeline_end = 0.0
    by_track = {}
    for i, c in enumerate(plan.get("clips") or []):
        where = f"clips[{i}]"
        if not all(_num(c.get(k)) for k in ("in", "out", "at")):
            errors.append(f"{where}: in, out and at must be numbers")
            continue
        speed = c.get("speed", 1.0)
        if not _num(speed) or speed <= 0:
            errors.append(f"{where}: speed must be > 0")
            speed = 1.0
        if c["in"] < 0 or c["at"] < 0:
            errors.append(f"{where}: in and at must be >= 0")
        if c["out"] <= c["in"]:
            errors.append(f"{where}: out ({c['out']}) must be after in ({c['in']})")
            continue
        src = info(c.get("file", ""), where)
        if src:
            if src["fps"] is None:
                errors.append(f"{where}: {c.get('file')} has no video stream")
            elif c["out"] > src["duration"] + 1 / fps:
                errors.append(f"{where}: out {c['out']}s is past the clip end ({round(src['duration'], 3)}s)")
        length = (c["out"] - c["in"]) / speed
        if length * fps < 1:
            errors.append(f"{where}: shorter than one frame on the timeline")
        track = c.get("track", 1)
        if not (isinstance(track, int) and track >= 1):
            errors.append(f"{where}: track must be an integer >= 1")
            track = 1
        by_track.setdefault(track, []).append((c["at"], c["at"] + length, i))
        timeline_end = max(timeline_end, c["at"] + length)
        if require_beats and (d := off_beat(c["at"])) is not None:
            warnings.append(f"{where}: starts {d:+}s off the nearest beat")

    for track, spans in by_track.items():
        spans.sort()
        for (s1, e1, i1), (s2, _, i2) in zip(spans, spans[1:], strict=False):
            if s2 < e1 - 0.5 / fps:
                errors.append(f"clips[{i1}] and clips[{i2}] overlap on track {track} ({round(e1 - s2, 3)}s)")
            elif s2 > e1 + 1.5 / fps:
                warnings.append(f"gap of {round(s2 - e1, 3)}s on track {track} before clips[{i2}]")

    for i, t in enumerate(plan.get("titles") or []):
        if not t.get("text"):
            errors.append(f"titles[{i}]: text is empty")
        if not (_num(t.get("at")) and t["at"] >= 0 and _num(t.get("duration")) and t["duration"] > 0):
            errors.append(f"titles[{i}]: at must be >= 0 and duration > 0")
    for i, mk in enumerate(plan.get("markers") or []):
        if not (_num(mk.get("at")) and mk["at"] >= 0):
            errors.append(f"markers[{i}]: at must be a number >= 0")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "clip_count": len(plan.get("clips") or []),
        "timeline_duration": round(timeline_end, 3),
        "plan_path": plan_path,
    }
