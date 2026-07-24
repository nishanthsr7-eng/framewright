import json
import os
import subprocess
import tempfile
from functools import partial

from framewright_core import output_root as _get_output_root
from framewright_core import run_ffmpeg


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
        raise RuntimeError(f"ffprobe failed: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    return {"has_audio": has_audio}


_run_ffmpeg = partial(run_ffmpeg, timeout=3600)


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def stabilize_video(input_path, smoothing=10, shakiness=5, zoom=0, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

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
