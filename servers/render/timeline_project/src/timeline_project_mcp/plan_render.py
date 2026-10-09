"""Render an edit plan (docs/edit-plan.md) to MP4 without Resolve: frame-exact cuts, speed, music, flash + shake, titles.
prepare_resolve bakes the same edit into per-cut media for resolve/scripts/Edit/Framewright/framewright_build_plan.lua."""

import json
import math
import os
import shutil
import subprocess
import tempfile
import time

from framewright_core import probe_video

from timeline_project_mcp.project import _get_output_root, _run_ffmpeg

PLATFORMS = {"tiktok": (1080, 1920)}
SHAKE_FRAMES = 6
SHAKE_PAD = 40
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]


def _repo_root():
    return os.path.dirname(_get_output_root())


def _font():
    path = os.path.join(_repo_root(), "servers", "assets", "text_overlay", "fonts", "Anton-Regular.ttf")
    return path if os.path.isfile(path) else None


def _full(path, base_dir):
    return path if os.path.isabs(path) else os.path.join(base_dir, path)


def _length(c):
    return (c["out"] - c["in"]) / c.get("speed", 1.0)


def _load(plan_path, base_dir):
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    proj = plan.get("project") or {}
    fps, w, h = proj.get("fps"), proj.get("width"), proj.get("height")
    if not (fps and w and h):
        raise ValueError("project.fps, width and height are required; run validate_plan first")
    clips = sorted([c for c in plan.get("clips") or [] if c.get("track", 1) == 1], key=lambda c: c["at"])
    if not clips:
        raise ValueError("No clips on track 1; this renderer only cuts track 1")
    for i, c in enumerate(clips):
        if not os.path.isfile(_full(c["file"], base_dir)):
            raise FileNotFoundError(f"clips[{i}] file {c['file']}")
        if c.get("speed", 1.0) <= 0 or c["out"] <= c["in"]:
            raise ValueError(f"clips[{i}]: needs out > in and speed > 0; run validate_plan first")
    end = max(c["at"] + _length(c) for c in clips)
    return plan, clips, fps, w, h, end, round(end * fps)


def _slots(clips, fps, total_frames):
    """(index, clip, start_frame, frames): each clip runs to the next cut, frame-exact so cuts stay on the beat."""
    out, cursor = [], 0
    for i, c in enumerate(clips):
        cursor = max(cursor, round(c["at"] * fps))  # a gap before this clip stays black
        nxt = round(clips[i + 1]["at"] * fps) if i + 1 < len(clips) else total_frames
        n = min(nxt, round((c["at"] + _length(c)) * fps)) - cursor
        if n > 0:
            out.append((i, c, cursor, n))
            cursor += n
    return out


def _cut_filter(c, fps, w, h):
    return (
        f"setpts=PTS/{c.get('speed', 1.0)},fps={fps},"
        f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1"
    )


def _effects(clips, fps):
    """Flash and shake windows as (start_s, end_s, expr of timeline t)."""
    flashes, shakes = [], []
    for c in clips:
        t = round(c["at"] * fps) / fps
        tr = c.get("transition_in") or {}
        if "flash" in str(tr.get("type", "")).lower():
            d = max(1, int(tr.get("frames", 3))) / fps
            flashes.append((t, t + d, f"between(t,{t:.4f},{t + d:.4f})*(1-(t-{t:.4f})/{d:.4f})"))
        if any("shake" in str(e).lower() for e in c.get("effects") or []):
            d = SHAKE_FRAMES / fps
            shakes.append((t, t + d, f"between(t,{t:.4f},{t + d:.4f})"))
    return flashes, shakes


def _fx_filters(w, h, flashes, shakes, any_shake):
    # any_shake: the shake zoom applies to the whole edit once any clip shakes
    chain = []
    if any_shake:
        sh, pad = "+".join(e for *_, e in shakes) or "0", SHAKE_PAD
        chain.append(
            f"scale={w + 2 * pad}:{h + 2 * pad},crop={w}:{h}:"
            f"x='{pad}+({sh})*{pad}*sin(t*90)':y='{pad}+({sh})*{pad}*cos(t*77)'"
        )
    if flashes:
        chain.append(f"eq=brightness='0.9*({'+'.join(e for *_, e in flashes)})':eval=frame")
    return chain


def _drawtext(i, t, ow, oh, font, tmp, enable=True):
    with open(os.path.join(tmp, f"title{i}.txt"), "w", encoding="utf-8") as f:
        f.write(str(t["text"]))
    size = int(min(ow, oh) * (0.09 if ow < oh else 0.11))
    a, b = float(t["at"]), float(t["at"]) + float(t["duration"])
    return (
        f"drawtext=textfile=title{i}.txt:{'fontfile=font.ttf:' if font else ''}fontsize={size}:"
        f"fontcolor=white:borderw={max(2, size // 14)}:bordercolor=black:"
        f"x=(w-text_w)/2:y=(h-text_h)/2" + (f":enable='between(t,{a:.3f},{b:.3f})'" if enable else "")
    )


def _ffmpeg_in(cwd, args, timeout):
    # cwd: titles reference font/text files by relative name, avoiding Windows path escaping
    r = subprocess.run(
        ["ffmpeg", "-y", "-v", "error"] + args,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {r.stderr[-1500:]}")


def _music_args(plan, base_dir, end):
    music = plan.get("music")
    if not (music and music.get("file")):
        return None
    mpath = _full(music["file"], base_dir)
    if not os.path.isfile(mpath):
        raise FileNotFoundError(f"music file {music['file']}")
    fade = min(1.5, end / 4)
    af = f"volume={music.get('gain_db', 0)}dB,afade=t=out:st={end - fade:.3f}:d={fade:.3f}"
    return ["-ss", str(music.get("start", 0.0)), "-i", mpath], af


def render_plan(
    plan_path: str,
    output_path: str | None = None,
    platform: str = "none",
    base_dir: str | None = None,
    crf: int = 18,
) -> dict:
    base_dir = base_dir or _repo_root()
    plan, clips, fps, w, h, end, total_frames = _load(plan_path, base_dir)
    skipped = len(plan.get("clips") or []) - len(clips)
    if output_path is None:
        out_dir = os.path.join(_get_output_root(), "plans")
        os.makedirs(out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(plan_path))[0]
        output_path = os.path.join(out_dir, f"{stem}{'_' + platform if platform != 'none' else ''}.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="render_plan_")
    try:
        segs, cursor = [], 0
        for i, c, start_f, n in _slots(clips, fps, total_frames):
            if start_f > cursor:  # gap -> black
                p = os.path.join(tmp, f"gap{i:04d}.mp4")
                _run_ffmpeg(
                    ["-v", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={fps}", "-frames:v"]
                    + [str(start_f - cursor)]
                    + ENC
                    + [p],
                    timeout=600,
                )
                segs.append(p)
            p = os.path.join(tmp, f"{i:04d}.mp4")
            vf = _cut_filter(c, fps, w, h) + ",tpad=stop_mode=clone:stop=-1"
            _run_ffmpeg(
                ["-v", "error", "-ss", str(c["in"]), "-i", _full(c["file"], base_dir), "-an", "-vf", vf]
                + ["-frames:v", str(n)]
                + ENC
                + [p],
                timeout=600,
            )
            segs.append(p)
            cursor = start_f + n
        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.write("\n".join(f"file '{os.path.basename(s)}'" for s in segs))
        cut = os.path.join(tmp, "cut.mp4")
        _run_ffmpeg(["-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", cut], timeout=600)

        flashes, shakes = _effects(clips, fps)
        chain = _fx_filters(w, h, flashes, shakes, bool(shakes))
        ow, oh = w, h
        if platform in PLATFORMS:
            ow, oh = PLATFORMS[platform]
            chain.append(f"scale=-2:{oh},crop={ow}:{oh}")  # center crop to 9:16
        # titles go after the crop so they stay inside the frame
        titles = plan.get("titles") or []
        font = _font()
        chain += [_drawtext(i, t, ow, oh, font, tmp) for i, t in enumerate(titles)]
        if font and titles:
            shutil.copy(font, os.path.join(tmp, "font.ttf"))
        chain.append("format=yuv420p")

        args = ["-i", cut]
        music = _music_args(plan, base_dir, end)
        if music:
            args += music[0]
            graph = f"[0:v]{','.join(chain)}[v];[1:a]{music[1]}[a]"
            maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        else:
            graph = f"[0:v]{','.join(chain)}[v]"
            maps = ["-map", "[v]"]
        out_abs = os.path.abspath(output_path)
        _ffmpeg_in(
            tmp,
            args
            + ["-filter_complex", graph]
            + maps
            + ["-t", f"{total_frames / fps:.4f}", "-r", str(fps), "-c:v", "libx264", "-preset", "medium"]
            + ["-crf", str(crf), out_abs],
            timeout=1800,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    info = probe_video(out_abs)
    return {
        "output_path": out_abs,
        "duration": round(info.duration, 3),
        "expected_duration": round(end, 3),
        "width": info.width,
        "height": info.height,
        "cuts": len(clips),
        "flashes": len(flashes),
        "shakes": len(shakes),
        "titles": len(titles),
        "skipped_other_tracks": skipped,
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


def prepare_resolve(plan_path: str, platform: str = "none", base_dir: str | None = None) -> dict:
    """Bake every cut exactly as render_plan draws it (speed, flash, shake, crop), titles as alpha overlays
    and the music with its gain and fade, then write output/framewright_plan.lua that places them 1:1."""
    base_dir = base_dir or _repo_root()
    plan, clips, fps, w, h, end, total_frames = _load(plan_path, base_dir)
    stem = os.path.splitext(os.path.basename(plan_path))[0]
    # new folder per run: Resolve caches media by path, so files are never overwritten under it
    out_dir = os.path.join(_get_output_root(), "resolve", f"{stem}_{time.strftime('%Y%m%d-%H%M%S')}")
    os.makedirs(out_dir, exist_ok=True)
    absp = lambda p: os.path.abspath(p).replace("\\", "/")
    ow, oh = PLATFORMS.get(platform, (w, h))

    flashes, shakes = _effects(clips, fps)
    lua_clips, markers = [], list(plan.get("markers") or [])
    for i, c, start_f, n in _slots(clips, fps, total_frames):
        a, b = start_f / fps, (start_f + n) / fps

        def near(ws, a=a, b=b):
            return [x for x in ws if x[0] < b and x[1] > a]

        # shift t to timeline time so flash/shake match the full render frame for frame
        vf = [_cut_filter(c, fps, w, h), "tpad=stop_mode=clone:stop=-1", f"setpts=PTS+{start_f}/({fps}*TB)"]
        vf += _fx_filters(w, h, near(flashes), near(shakes), bool(shakes))
        if platform in PLATFORMS:
            vf.append(f"scale=-2:{oh},crop={ow}:{oh}")
        vf += ["setpts=PTS-STARTPTS", "format=yuv420p"]
        p = os.path.join(out_dir, f"cut_{i + 1:03d}.mp4")
        _run_ffmpeg(
            ["-v", "error", "-ss", str(c["in"]), "-i", _full(c["file"], base_dir), "-an", "-vf", ",".join(vf)]
            + ["-frames:v", str(n), "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "12"]
            + ["-pix_fmt", "yuv420p", p],
            timeout=600,
        )
        lua_clips.append({"file": absp(p), "in": 0, "out": n / fps, "at": a, "track": 1})
        tr, notes = c.get("transition_in") or {}, []
        if tr:
            notes.append(f"{tr.get('type')} ({tr.get('frames', 3)}f)")
        notes += [str(e) for e in c.get("effects") or []]
        if c.get("speed", 1.0) != 1:
            notes.append(f"{c['speed']}x")
        if notes:
            markers.append({"at": a, "color": "Pink", "name": "baked: " + ", ".join(notes)})

    # titles: transparent ProRes 4444 overlays covering exactly the frames render_plan draws them on
    titles, font, lanes = plan.get("titles") or [], _font(), []
    tmp = tempfile.mkdtemp(prefix="prepare_resolve_")
    try:
        if font and titles:
            shutil.copy(font, os.path.join(tmp, "font.ttf"))
        for i, t in enumerate(titles):
            a3, b3 = round(float(t["at"]), 3), round(float(t["at"]) + float(t["duration"]), 3)
            k0, k1 = math.ceil(a3 * fps - 1e-6), min(math.floor(b3 * fps + 1e-6), total_frames - 1)
            if k1 < k0:
                continue
            lane = next((j for j, last in enumerate(lanes) if last <= k0), len(lanes))
            lanes[lane : lane + 1] = [k1 + 1]
            p = os.path.join(out_dir, f"title_{i + 1:02d}.mov")
            src = f"color=c=black@0.0:s={ow}x{oh}:r={fps},format=rgba," + _drawtext(i, t, ow, oh, font, tmp, False)
            _ffmpeg_in(
                tmp,
                ["-f", "lavfi", "-i", src, "-frames:v", str(k1 - k0 + 1), "-c:v", "prores_ks", "-profile:v", "4444"]
                + ["-pix_fmt", "yuva444p10le", absp(p)],
                timeout=600,
            )
            lua_clips.append(
                {"file": absp(p), "in": 0, "out": (k1 - k0 + 1) / fps, "at": k0 / fps, "track": 2 + lane, "alpha": True}
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    music = _music_args(plan, base_dir, end)
    lua_music = None
    if music:
        p = os.path.join(out_dir, "music.wav")
        _run_ffmpeg(
            ["-v", "error"] + music[0] + ["-af", music[1], "-t", f"{total_frames / fps:.4f}", "-c:a", "pcm_s16le", p],
            timeout=600,
        )
        lua_music = {"file": absp(p), "start": 0}

    proj: dict = dict(plan.get("project") or {}, width=ow, height=oh, fps=fps)
    proj.setdefault("name", stem)
    out = {"source": absp(plan_path), "project": proj, "clips": lua_clips, "markers": markers, "exact": True}
    if lua_music:
        out["music"] = lua_music
    lua_path = os.path.join(_get_output_root(), "framewright_plan.lua")
    with open(lua_path, "w", encoding="utf-8") as f:
        f.write("return " + _lua(out) + "\n")  # loaded with dofile (Resolve's Lua has no io)
    return {
        "output_path": absp(lua_path),
        "media_dir": absp(out_dir),
        "cuts": len(lua_clips) - sum(1 for c in lua_clips if c.get("alpha")),
        "titles": sum(1 for c in lua_clips if c.get("alpha")),
        "flashes": len(flashes),
        "shakes": len(shakes),
        "width": ow,
        "height": oh,
        "frames": total_frames,
    }
