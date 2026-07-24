import json
import os
import subprocess
import tempfile

from framewright_core import output_root as _get_output_root
from framewright_core import run_ffmpeg as _run_ffmpeg


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
        raise RuntimeError(f"ffprobe failed: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    duration = float(data["format"].get("duration") or 0.0)
    if vstream:
        num, den = (vstream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
        fps = float(num) / float(den) if float(den) != 0 else 30.0
    else:
        fps = 30.0
    return {"has_audio": has_audio, "duration": duration, "fps": fps}


def _atempo_chain(speed):
    filters = []
    s = float(speed)
    while s > 2.0:
        filters.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        filters.append("atempo=0.5")
        s /= 0.5
    filters.append(f"atempo={s:.6f}")
    return ",".join(filters)


def _speed_vf(speed, fps, smooth):
    speed = float(speed)
    vf = f"setpts={1.0 / speed:.6f}*PTS"
    if smooth and speed < 1.0:
        vf += f",minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:vsbmc=1"
    return vf


def change_speed(input_path, speed=1.0, smooth=True, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    speed = float(speed)
    if speed <= 0:
        raise ValueError("speed must be greater than 0")

    info = _probe(input_path)
    vf = _speed_vf(speed, info["fps"], smooth)

    if output_path is None:
        output_path = _default_output_path(input_path, "speed")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-i", input_path, "-vf", vf]
    if info["has_audio"]:
        args += ["-af", _atempo_chain(speed), "-c:a", "aac"]
    else:
        args += ["-an"]
    args += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", output_path]
    _run_ffmpeg(args)

    new_duration = info["duration"] / speed
    return {"output_path": output_path, "speed": speed, "smooth": smooth, "new_duration": round(new_duration, 3)}


def speed_ramp(input_path, segments, output_path=None):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    if not segments:
        raise ValueError("segments is empty")

    info = _probe(input_path)

    if output_path is None:
        output_path = _default_output_path(input_path, "ramp")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        seg_files = []
        for i, seg in enumerate(segments):
            start = float(seg["start"])
            end = float(seg["end"])
            speed = float(seg.get("speed", 1.0))
            smooth = seg.get("smooth", True)
            if end <= start:
                raise ValueError(f"segment {i}: end must be greater than start")
            if speed <= 0:
                raise ValueError(f"segment {i}: speed must be greater than 0")

            seg_path = os.path.join(tmp, f"seg_{i:03d}.mp4")
            vf = _speed_vf(speed, info["fps"], smooth)
            args = ["-ss", f"{start}", "-i", input_path, "-t", f"{end - start}", "-vf", vf]
            if info["has_audio"]:
                args += ["-af", _atempo_chain(speed), "-c:a", "aac"]
            else:
                args += ["-an"]
            args += ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p", seg_path]
            _run_ffmpeg(args)
            seg_files.append(seg_path)

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in seg_files:
                f.write(f"file '{seg}'\n")
        _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output_path])

    out_info = _probe(output_path)
    return {"output_path": output_path, "segment_count": len(segments), "duration": round(out_info["duration"], 3)}
