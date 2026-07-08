import json
import os
import subprocess
import tempfile


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
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    return {"has_audio": has_audio}


def _run_ffmpeg(args, timeout=3600, cwd=None):
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 失败: {result.stderr[-1500:]}")


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def stabilize_video(input_path, smoothing=10, shakiness=5, zoom=0, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"找不到文件: {input_path}")

    info = _probe(input_path)
    shakiness = max(1, min(10, int(shakiness)))
    smoothing = max(0, int(smoothing))

    if output_path is None:
        output_path = _default_output_path(input_path, "stabilized")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        trf_path = os.path.join(tmp, "transforms.trf")
        trf_escaped = _escape_filter_path(trf_path)

        # Pass 1: analyze motion
        _run_ffmpeg([
            "-i", input_path,
            "-vf", f"vidstabdetect=shakiness={shakiness}:accuracy=15:result='{trf_escaped}'",
            "-f", "null", "-",
        ])

        # Pass 2: apply stabilizing transform
        vf = (
            f"vidstabtransform=input='{trf_escaped}':zoom={zoom}:smoothing={smoothing},"
            f"unsharp=5:5:0.8:3:3:0.4"
        )
        args = ["-i", input_path, "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p"]
        if info["has_audio"]:
            args += ["-c:a", "copy"]
        args += [output_path]
        _run_ffmpeg(args)

    return {"output_path": output_path, "smoothing": smoothing, "shakiness": shakiness, "zoom": zoom}
