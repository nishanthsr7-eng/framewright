"""Render an edit plan (docs/edit-plan.md) to MP4 without Resolve: frame-exact cuts, speed, music, flash + shake, titles."""
import json
import os
import shutil
import subprocess
import tempfile

from timeline_project_mcp.project import _get_output_root, _probe, _run_ffmpeg

PLATFORMS = {"tiktok": (1080, 1920)}
SHAKE_FRAMES = 6
SHAKE_PAD = 40


def _repo_root():
    return os.path.dirname(_get_output_root())


def _font():
    path = os.path.join(_repo_root(), "servers", "assets", "text_overlay", "fonts", "Anton-Regular.ttf")
    return path if os.path.isfile(path) else None


def _full(path, base_dir):
    return path if os.path.isabs(path) else os.path.join(base_dir, path)


def render_plan(plan_path, output_path=None, platform="none", base_dir=None, crf=18):
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    base_dir = base_dir or _repo_root()
    proj = plan.get("project") or {}
    fps, w, h = proj.get("fps"), proj.get("width"), proj.get("height")
    if not (fps and w and h):
        raise ValueError("project.fps, width and height are required; run validate_plan first")
    clips = sorted([c for c in plan.get("clips") or [] if c.get("track", 1) == 1], key=lambda c: c["at"])
    skipped = len(plan.get("clips") or []) - len(clips)
    if not clips:
        raise ValueError("No clips on track 1; this renderer only cuts track 1")
    for i, c in enumerate(clips):
        src = _full(c["file"], base_dir)
        if not os.path.isfile(src):
            raise FileNotFoundError(f"clips[{i}] file {c['file']}")
        if c.get("speed", 1.0) <= 0 or c["out"] <= c["in"]:
            raise ValueError(f"clips[{i}]: needs out > in and speed > 0; run validate_plan first")

    def length(c):
        return (c["out"] - c["in"]) / c.get("speed", 1.0)

    end = max(c["at"] + length(c) for c in clips)
    total_frames = round(end * fps)
    if output_path is None:
        out_dir = os.path.join(_get_output_root(), "plans")
        os.makedirs(out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(plan_path))[0]
        output_path = os.path.join(out_dir, f"{stem}{'_' + platform if platform != 'none' else ''}.mp4")
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="render_plan_")
    try:
        segs = []
        enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p"]
        cursor = 0  # frames
        for i, c in enumerate(clips):
            start_f = round(c["at"] * fps)
            if start_f > cursor:  # gap -> black
                p = os.path.join(tmp, f"gap{i:04d}.mp4")
                _run_ffmpeg(["-v", "error", "-f", "lavfi", "-i", f"color=black:s={w}x{h}:r={fps}",
                             "-frames:v", str(start_f - cursor)] + enc + [p], timeout=600)
                segs.append(p)
                cursor = start_f
            nxt = round(clips[i + 1]["at"] * fps) if i + 1 < len(clips) else total_frames
            n = min(nxt, round((c["at"] + length(c)) * fps)) - cursor  # frame-exact so cuts stay on the beat
            if n <= 0:
                continue
            p = os.path.join(tmp, f"{i:04d}.mp4")
            vf = (f"setpts=PTS/{c.get('speed', 1.0)},fps={fps},"
                  f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1")
            _run_ffmpeg(["-v", "error", "-ss", str(c["in"]), "-i", _full(c["file"], base_dir), "-an",
                         "-vf", vf + ",tpad=stop_mode=clone:stop=-1", "-frames:v", str(n)] + enc + [p],
                        timeout=600)
            segs.append(p)
            cursor += n
        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            f.write("\n".join(f"file '{os.path.basename(s)}'" for s in segs))
        cut = os.path.join(tmp, "cut.mp4")
        _run_ffmpeg(["-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", cut], timeout=600)

        # flash (decays over transition frames) + shake on marked clips
        flashes, shakes = [], []
        for c in clips:
            t = round(c["at"] * fps) / fps
            tr = c.get("transition_in") or {}
            if "flash" in str(tr.get("type", "")).lower():
                d = max(1, int(tr.get("frames", 3))) / fps
                flashes.append(f"between(t,{t:.4f},{t + d:.4f})*(1-(t-{t:.4f})/{d:.4f})")
            if any("shake" in str(e).lower() for e in c.get("effects") or []):
                shakes.append(f"between(t,{t:.4f},{t + SHAKE_FRAMES / fps:.4f})")
        chain = []
        if shakes:
            sh, pad = "+".join(shakes), SHAKE_PAD
            chain.append(f"scale={w + 2 * pad}:{h + 2 * pad},crop={w}:{h}:"
                         f"x='{pad}+({sh})*{pad}*sin(t*90)':y='{pad}+({sh})*{pad}*cos(t*77)'")
        if flashes:
            chain.append(f"eq=brightness='0.9*({'+'.join(flashes)})':eval=frame")
        ow, oh = w, h
        if platform in PLATFORMS:
            ow, oh = PLATFORMS[platform]
            chain.append(f"scale=-2:{oh},crop={ow}:{oh}")  # center crop to 9:16
        # titles go after the crop so they stay inside the frame
        titles = plan.get("titles") or []
        font = _font()
        for i, t in enumerate(titles):
            with open(os.path.join(tmp, f"title{i}.txt"), "w", encoding="utf-8") as f:
                f.write(str(t["text"]))
            size = int(min(ow, oh) * (0.09 if ow < oh else 0.11))
            a, b = float(t["at"]), float(t["at"]) + float(t["duration"])
            chain.append(f"drawtext=textfile=title{i}.txt:{'fontfile=font.ttf:' if font else ''}fontsize={size}:"
                         f"fontcolor=white:borderw={max(2, size // 14)}:bordercolor=black:"
                         f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{a:.3f},{b:.3f})'")
        if font and titles:
            shutil.copy(font, os.path.join(tmp, "font.ttf"))
        chain.append("format=yuv420p")

        args = ["-v", "error", "-i", cut]
        music = plan.get("music")
        if music and music.get("file"):
            mpath = _full(music["file"], base_dir)
            if not os.path.isfile(mpath):
                raise FileNotFoundError(f"music file {music['file']}")
            args += ["-ss", str(music.get("start", 0.0)), "-i", mpath]
            fade = min(1.5, end / 4)
            audio = (f"[1:a]volume={music.get('gain_db', 0)}dB,"
                     f"afade=t=out:st={end - fade:.3f}:d={fade:.3f}[a]")
            graph = f"[0:v]{','.join(chain)}[v];{audio}"
            maps = ["-map", "[v]", "-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
        else:
            graph = f"[0:v]{','.join(chain)}[v]"
            maps = ["-map", "[v]"]
        out_abs = os.path.abspath(output_path)
        # cwd=tmp: titles reference font/text files by relative name, avoiding Windows path escaping
        r = subprocess.run(["ffmpeg", "-y"] + args + ["-filter_complex", graph] + maps +
                           ["-t", f"{total_frames / fps:.4f}", "-r", str(fps), "-c:v", "libx264", "-preset",
                            "medium", "-crf", str(crf), out_abs], capture_output=True, text=True, timeout=1800, cwd=tmp)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {r.stderr[-1500:]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    info = _probe(out_abs)
    return {"output_path": out_abs, "duration": round(info["duration"], 3), "expected_duration": round(end, 3),
            "width": info["width"], "height": info["height"], "cuts": len(clips), "flashes": len(flashes),
            "shakes": len(shakes), "titles": len(titles), "skipped_other_tracks": skipped}
