import json
import os
import subprocess

ASSETS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "assets")
LIGHT_LEAK_STYLES = {"warm", "golden", "cool", "white"}
PAN_DIRECTIONS = {"left_to_right", "right_to_left", "static"}


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


def _default_output_path(input_path, suffix):
    base = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1] or ".mp4"
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
    duration = float(data["format"].get("duration") or 0.0)
    return {"width": width, "height": height, "has_audio": has_audio, "duration": duration}


def _run_ffmpeg(args, timeout=1800):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def add_film_grain(input_path, intensity=20, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")
    info = _probe(input_path)
    intensity = max(0, min(100, int(intensity)))

    if output_path is None:
        output_path = _default_output_path(input_path, "grain")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    vf = f"noise=alls={intensity}:allf=t+u"
    args = ["-i", input_path, "-vf", vf]
    if info["has_audio"]:
        args += ["-c:a", "copy"]
    args += [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "intensity": intensity}


def add_vignette(input_path, intensity=0.5, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")
    info = _probe(input_path)
    intensity = max(0.0, min(1.0, float(intensity)))

    if output_path is None:
        output_path = _default_output_path(input_path, "vignette")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # angle ranges roughly PI/5 (subtle) .. 3PI/5 (strong)
    angle = (3.14159265 / 5.0) + intensity * (3.14159265 * 2.0 / 5.0)
    vf = f"vignette=angle={angle:.5f}"
    args = ["-i", input_path, "-vf", vf]
    if info["has_audio"]:
        args += ["-c:a", "copy"]
    args += [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "intensity": intensity}


def add_chromatic_aberration(input_path, shift=3, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")
    info = _probe(input_path)
    shift = int(shift)

    if output_path is None:
        output_path = _default_output_path(input_path, "chroma_ab")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    vf = f"rgbashift=rh={shift}:bh={-shift}"
    args = ["-i", input_path, "-vf", vf]
    if info["has_audio"]:
        args += ["-c:a", "copy"]
    args += [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "shift": shift}


def add_light_leak(input_path, style="warm", intensity=0.5, pan="left_to_right", output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")
    if style not in LIGHT_LEAK_STYLES:
        raise ValueError(f"style 必须是: {', '.join(sorted(LIGHT_LEAK_STYLES))}")
    if pan not in PAN_DIRECTIONS:
        raise ValueError(f"pan 必须是: {', '.join(sorted(PAN_DIRECTIONS))}")

    info = _probe(input_path)
    intensity = max(0.0, min(1.0, float(intensity)))
    w, h, duration = info["width"], info["height"], max(info["duration"], 0.1)
    asset_path = os.path.join(ASSETS_DIR, f"{style}.png")

    if output_path is None:
        output_path = _default_output_path(input_path, "light_leak")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if pan == "static":
        crop_x = "(in_w-out_w)/2"
    elif pan == "left_to_right":
        crop_x = f"(in_w-out_w)*t/{duration}"
    else:
        crop_x = f"(in_w-out_w)*(1-t/{duration})"

    filter_complex = (
        f"[1:v]scale={2 * w}:{h},crop=w={w}:h={h}:x='{crop_x}':y=0[leak];"
        f"[0:v][leak]blend=all_mode=screen:all_opacity={intensity}[vout]"
    )

    args = ["-i", input_path, "-loop", "1", "-i", asset_path,
            "-filter_complex", filter_complex, "-map", "[vout]"]
    if info["has_audio"]:
        args += ["-map", "0:a", "-c:a", "copy"]
    args += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
             "-t", f"{duration}", output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "style": style, "intensity": intensity, "pan": pan}
