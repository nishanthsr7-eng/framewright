import os
import subprocess

LUTS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "luts")

BUILTIN_LUTS = {
    "cinematic_teal_orange": "经典电影感: 阴影偏青色，高光偏橙色",
    "warm_vintage": "温暖复古: 提升黑位、暖色调、轻微降低饱和度",
    "cool_blue": "冷调蓝色: 增加蓝色、轻微降低高光饱和度，适合夜景/科技感",
    "high_contrast_bw": "高对比度黑白",
    "faded_film": "褪色胶片感: 提升黑位、压缩高光、降低饱和度",
    "moody_green": "暗绿色调: 压暗阴影并偏绿，适合悬疑/惊悚氛围",
    "bleach_bypass": "漂白效果: 大幅降低饱和度并提升对比度，适合战争/动作片",
}


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


def _default_output_path(input_path, suffix, ext=None):
    base = os.path.splitext(os.path.basename(input_path))[0]
    ext = ext or os.path.splitext(input_path)[1] or ".mp4"
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_{suffix}{ext}")


def _probe(path):
    cmd = ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr[-1000:]}")
    import json
    data = json.loads(result.stdout)
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    has_video = any(s["codec_type"] == "video" for s in data["streams"])
    duration = float(data["format"].get("duration") or 0.0)
    return {"has_video": has_video, "has_audio": has_audio, "duration": duration}


def _run_ffmpeg(args, timeout=1800):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def list_luts():
    return {name: {"description": desc, "path": os.path.join(LUTS_DIR, f"{name}.cube")}
            for name, desc in BUILTIN_LUTS.items()}


def _resolve_lut_path(lut):
    if lut in BUILTIN_LUTS:
        return os.path.join(LUTS_DIR, f"{lut}.cube")
    if os.path.exists(lut):
        return lut
    raise FileNotFoundError(
        f"未找到 LUT: {lut}。可用内置 LUT: {', '.join(BUILTIN_LUTS.keys())}，"
        f"或提供一个存在的 .cube 文件路径。"
    )


def apply_lut(input_path, lut, intensity=1.0, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    info = _probe(input_path)
    if not info["has_video"]:
        raise RuntimeError(f"文件没有视频流: {input_path}")

    lut_path = _resolve_lut_path(lut)
    lut_escaped = _escape_filter_path(lut_path)

    intensity = max(0.0, min(1.0, float(intensity)))
    if output_path is None:
        output_path = _default_output_path(input_path, "graded")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-i", input_path]
    if intensity >= 0.999:
        args += ["-vf", f"lut3d=file='{lut_escaped}'"]
    else:
        filter_complex = (
            f"[0:v]split[orig][toL];"
            f"[toL]lut3d=file='{lut_escaped}'[graded];"
            f"[orig][graded]blend=all_mode=normal:all_opacity={intensity}[vout]"
        )
        args += ["-filter_complex", filter_complex, "-map", "[vout]"]
        if info["has_audio"]:
            args += ["-map", "0:a"]

    if info["has_audio"]:
        args += ["-c:a", "copy"]
    args += [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "lut": lut, "intensity": intensity}
