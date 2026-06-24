import json
import os
import subprocess

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


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
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    width = int(vstream["width"]) if vstream else None
    height = int(vstream["height"]) if vstream else None
    duration = float(data["format"].get("duration") or (vstream.get("duration") if vstream else 0) or 0.0)
    return {"width": width, "height": height, "duration": duration, "has_audio": has_audio}


def _run_ffmpeg(args, timeout=1800):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def _is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def remove_background(input_path, color="0x00FF00", similarity=0.18, blend=0.05, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    info = _probe(input_path)
    vf = f"chromakey=color={color}:similarity={similarity}:blend={blend},format=yuva420p"

    if output_path is None:
        output_path = _default_output_path(input_path, "keyed", ext=".webm")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-i", input_path, "-vf", vf, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-an", output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "color": color, "similarity": similarity, "blend": blend}


def replace_background(foreground_path, background_path, color="0x00FF00", similarity=0.18,
                        blend=0.05, output_path=None):
    if not os.path.exists(foreground_path):
        raise FileNotFoundError(f"找不到前景文件: {foreground_path}")
    if not os.path.exists(background_path):
        raise FileNotFoundError(f"找不到背景文件: {background_path}")

    fg_info = _probe(foreground_path)
    w, h = fg_info["width"], fg_info["height"]
    duration = fg_info["duration"]

    input_args = ["-i", foreground_path]
    if _is_image(background_path):
        input_args += ["-loop", "1", "-t", f"{duration}", "-i", background_path]
    else:
        bg_info = _probe(background_path)
        if bg_info["duration"] < duration:
            input_args += ["-stream_loop", "-1", "-i", background_path]
        else:
            input_args += ["-i", background_path]

    filter_complex = (
        f"[0:v]chromakey=color={color}:similarity={similarity}:blend={blend},format=yuva420p[fg];"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[bg];"
        f"[bg][fg]overlay=shortest=1[vout]"
    )

    if output_path is None:
        output_path = _default_output_path(foreground_path, "bg_replaced")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = input_args + ["-filter_complex", filter_complex, "-map", "[vout]"]
    if fg_info["has_audio"]:
        args += ["-map", "0:a", "-c:a", "aac"]
    args += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", "-t", f"{duration}", output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "color": color, "similarity": similarity, "blend": blend}
