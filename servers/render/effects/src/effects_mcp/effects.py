import json
import os
import subprocess


def _find_tools_dir():
    path = os.path.abspath(os.path.dirname(__file__))
    while True:
        parent, name = os.path.split(path)
        if name == "servers":
            return path
        if parent == path:
            return None
        path = parent


def _get_output_root():
    tools_dir = _find_tools_dir()
    if tools_dir is not None:
        return os.path.join(os.path.dirname(tools_dir), "output")
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), "output")


def _probe(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if vstream is None:
        raise RuntimeError(f"未找到视频流: {video_path}")
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


def _run_ffmpeg(args, timeout=600):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


EFFECTS = {
    "zoom_punch": "短促的放大冲击(由内而外猛地放大再恢复)，常用于打击/强调瞬间",
    "shake": "快速抖动(模拟撞击/震动)",
    "rgb_split": "RGB 通道分离(色差/故障风格)",
    "flash": "短促白色闪光，常用于卡点强调",
    "vignette": "暗角(画面四周变暗，聚焦中心)",
    "glow": "柔光/光晕(画面发光、提亮高光)",
    "film_grain": "胶片噪点颗粒",
    "light_leak": "暖色调光漏(暖色调色风格叠加)",
    "speed_ramp": "整体变速(慢动作或快进)",
    "grade_warm": "暖色调色(偏橙黄，怀旧/温暖感)",
    "grade_cool": "冷色调色(偏蓝青，冷峻/科技感)",
    "grade_high_contrast": "高对比度调色(更强的明暗对比和饱和度)",
    "grade_faded": "褪色风格调色(降低对比度和饱和度，复古胶片感)",
    "grade_punchy": "高饱和高对比\"剪辑风\"调色(动漫/游戏剪辑常用)",
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

    raise ValueError(f"未知特效: {effect}，可用特效: {list(EFFECTS.keys())}")


def apply_effect(video_path, effect, intensity=1.0, start_time=0.0, duration=None, output_path=None):
    """
    在视频上应用一个"剪辑风格"特效。

    effect: EFFECTS 中的特效名称之一。
    intensity: 特效强度，约 0.5(轻微)~2.0(强烈)，默认 1.0。
    start_time/duration: 特效生效的时间区间(秒)。除 speed_ramp/grade_* (作用于整段视频)
      以外的特效，仅在该区间内生效，区间外画面不变。duration 默认覆盖到视频结尾。
    """
    if effect not in EFFECTS:
        raise ValueError(f"未知特效: {effect}，可用特效: {list(EFFECTS.keys())}")

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
        raise ValueError(f"未知转场: {transition}，可用转场: {TRANSITIONS}")

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
