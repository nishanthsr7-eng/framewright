import json
import os
import subprocess
from functools import partial

from framewright_core import output_root as _get_output_root
from framewright_core import run_ffmpeg


def _probe(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if vstream is None:
        raise RuntimeError(f"No video stream in: {video_path}")
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    width = int(vstream["width"])
    height = int(vstream["height"])
    duration = float(data["format"].get("duration") or vstream.get("duration") or 0.0)
    num, den = (vstream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) != 0 else 30.0
    return {"width": width, "height": height, "duration": duration, "fps": fps, "has_audio": has_audio}


def _default_output_path(video_path, suffix):
    base, ext = os.path.splitext(os.path.basename(video_path))
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_{suffix}{ext if ext else '.mp4'}")


_run_ffmpeg = partial(run_ffmpeg, timeout=600)


EFFECTS = {
    "zoom_punch": "Quick zoom punch-in and back, for hits and emphasis",
    "shake": "Fast camera shake for impacts",
    "rgb_split": "RGB channel split, glitch look",
    "flash": "Short white flash on a beat",
    "vignette": "Darkened edges",
    "glow": "Soft bloom on highlights",
    "film_grain": "Film grain",
    "light_leak": "Warm light-leak tint",
    "speed_ramp": "Whole-clip speed change",
    "grade_warm": "Warm grade",
    "grade_cool": "Cool grade",
    "grade_high_contrast": "High-contrast grade",
    "grade_faded": "Faded film grade",
    "grade_punchy": "Punchy saturated edit grade",
}

TRANSITIONS = [
    "fade", "fadeblack", "fadewhite", "dissolve", "pixelize",
    "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "smoothleft", "smoothright", "smoothup", "smoothdown",
    "circlecrop", "rectcrop", "circleopen", "circleclose",
    "vertopen", "vertclose", "horzopen", "horzclose",
    "diagtl", "diagtr", "diagbl", "diagbr",
    "hlslice", "hrslice", "vuslice", "vdslice",
    "hblur", "distance", "zoomin",
    "hlwind", "hrwind", "vuwind", "vdwind",
    "coverleft", "coverright", "coverup", "coverdown",
    "revealleft", "revealright", "revealup", "revealdown",
    "wipetl", "wipetr", "wipebl", "wipebr",
]


def list_effects():
    return EFFECTS


def list_transitions():
    return TRANSITIONS


def _build_filter(effect, info, intensity, start, end):
    w, h = info["width"], info["height"]
    btw = f"between(t,{start},{end})"

    if effect == "zoom_punch":
        mid = (start + end) / 2
        sigma = max((end - start) / 4, 0.05)
        amt = 0.35 * intensity
        zoom = f"(1+{amt}*exp(-((t-{mid})*(t-{mid}))/(2*{sigma}*{sigma})))"
        return (
            f"scale=w='{w}*{zoom}':h='{h}*{zoom}':eval=frame,"
            f"crop=w={w}:h={h}:x='(iw-ow)/2':y='(ih-oh)/2'"
        )

    if effect == "shake":
        amp = max(1, int(6 * intensity))
        return (
            f"crop=w='{w}-{2*amp}':h='{h}-{2*amp}':"
            f"x='{amp}+{amp}*sin(2*PI*9*(t-{start}))*{btw}':"
            f"y='{amp}+{amp}*cos(2*PI*11*(t-{start}))*{btw}',"
            f"scale={w}:{h}"
        )

    if effect == "rgb_split":
        px = max(1, int(round(3 * intensity)))
        return f"rgbashift=rh={px}:bh=-{px}:edge=smear:enable='{btw}'"

    if effect == "flash":
        flash_end = min(end, start + max(0.08, 0.15 * intensity))
        return f"eq=brightness='if(between(t,{start},{flash_end}),{min(intensity,1.0)},0)':eval=frame"

    if effect == "vignette":
        angle = 3.14159265 / max(0.5, 6 - 4 * min(intensity, 1.0))
        return f"vignette=angle={angle}:enable='{btw}'"

    if effect == "glow":
        sigma = 4 + 8 * intensity
        opacity = min(0.6, 0.25 * intensity)
        return (
            f"split[gb_a][gb_b];"
            f"[gb_b]gblur=sigma={sigma}:enable='{btw}'[gb_blur];"
            f"[gb_a][gb_blur]blend=all_mode=screen:all_opacity={opacity}:enable='{btw}'"
        )

    if effect == "film_grain":
        amt = int(10 + 30 * intensity)
        return f"noise=alls={amt}:allf=t+u:enable='{btw}'"

    if effect == "light_leak":
        warmth = min(40, int(15 * intensity))
        return (
            f"colorbalance=rh={0.01*warmth}:gh={0.003*warmth}:bh=-{0.01*warmth}:"
            f"rm={0.01*warmth}:bm=-{0.005*warmth}:enable='{btw}'"
        )

    if effect == "speed_ramp":
        factor = max(0.25, min(4.0, intensity))
        return ("__speed__", factor)

    if effect.startswith("grade_"):
        preset = effect[len("grade_"):]
        if preset == "warm":
            return "eq=saturation=1.1:gamma_r=1.05:gamma_b=0.95:contrast=1.05"
        if preset == "cool":
            return "eq=saturation=1.05:gamma_b=1.08:gamma_r=0.95:contrast=1.05"
        if preset == "high_contrast":
            return f"eq=contrast={1 + 0.4*intensity}:saturation={1 + 0.3*intensity}"
        if preset == "faded":
            return f"eq=contrast={1 - 0.2*intensity}:saturation={1 - 0.35*intensity}:brightness={0.05*intensity}"
        if preset == "punchy":
            return f"eq=contrast={1 + 0.25*intensity}:saturation={1 + 0.5*intensity}:gamma=1.05"

    raise ValueError(f"Unknown effect: {effect}. Available: {list(EFFECTS.keys())}")


def apply_effect(video_path, effect, intensity=1.0, start_time=0.0, duration=None, output_path=None):
    """
    在视频上应用一个"剪辑风格"特效。

    effect: EFFECTS 中的特效名称之一。
    intensity: 特效强度，约 0.5(轻微)~2.0(强烈)，默认 1.0。
    start_time/duration: 特效生效的时间区间(秒)。除 speed_ramp/grade_* (作用于整段视频)
      以外的特效，仅在该区间内生效，区间外画面不变。duration 默认覆盖到视频结尾。
    """
    if effect not in EFFECTS:
        raise ValueError(f"Unknown effect: {effect}. Available: {list(EFFECTS.keys())}")

    info = _probe(video_path)
    end_time = start_time + duration if duration is not None else info["duration"]

    result = _build_filter(effect, info, intensity, start_time, end_time)

    if output_path is None:
        output_path = _default_output_path(video_path, effect)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if isinstance(result, tuple) and result[0] == "__speed__":
        factor = result[1]
        vf = f"setpts=PTS/{factor}"
        args = ["-i", video_path, "-vf", vf]
        if info["has_audio"]:
            remaining = factor
            atempo_filters = []
            while remaining > 2.0:
                atempo_filters.append("atempo=2.0")
                remaining /= 2.0
            while remaining < 0.5:
                atempo_filters.append("atempo=0.5")
                remaining /= 0.5
            atempo_filters.append(f"atempo={remaining}")
            args += ["-af", ",".join(atempo_filters)]
        args += [output_path]
    else:
        args = ["-i", video_path, "-filter_complex", f"[0:v]{result}[v]", "-map", "[v]"]
        if info["has_audio"]:
            args += ["-map", "0:a", "-c:a", "copy"]
        args += [output_path]

    _run_ffmpeg(args)
    return {"output_path": output_path, "effect": effect, "intensity": intensity,
            "start_time": start_time, "end_time": end_time}


def apply_transition(video_a, video_b, transition="fade", duration=0.5, output_path=None):
    """
    在两个视频片段之间应用 xfade 转场，输出拼接后的视频(片段A -> 转场 -> 片段B)。

    transition: TRANSITIONS 中的转场名称之一。
    duration: 转场持续时间(秒)。
    """
    if transition not in TRANSITIONS:
        raise ValueError(f"Unknown transition: {transition}. Available: {TRANSITIONS}")

    info_a = _probe(video_a)
    info_b = _probe(video_b)
    w, h, fps = info_a["width"], info_a["height"], info_a["fps"]
    offset = max(0.0, info_a["duration"] - duration)

    if output_path is None:
        base_a = os.path.splitext(os.path.basename(video_a))[0]
        out_dir = os.path.join(_get_output_root(), base_a)
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"{base_a}_{transition}_transition.mp4")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    vfilter = (
        f"[1:v]scale={w}:{h},setsar=1,fps={fps},settb=AVTB[v1];"
        f"[0:v]setsar=1,fps={fps},settb=AVTB[v0];"
        f"[v0][v1]xfade=transition={transition}:duration={duration}:offset={offset}[v]"
    )

    args = ["-i", video_a, "-i", video_b, "-filter_complex"]
    has_audio = info_a["has_audio"] and info_b["has_audio"]
    if has_audio:
        afilter = f"[0:a][1:a]acrossfade=d={duration}[a]"
        args += [vfilter + ";" + afilter, "-map", "[v]", "-map", "[a]"]
    else:
        args += [vfilter, "-map", "[v]"]
        if info_a["has_audio"]:
            args += ["-map", "0:a"]

    args += [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "transition": transition, "duration": duration}
