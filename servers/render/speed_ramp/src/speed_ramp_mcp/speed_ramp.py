import os
import tempfile

from framewright_core import default_output_path, probe_video, video_codec_args
from framewright_core import run_ffmpeg as _run_ffmpeg


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


def change_speed(
    input_path: str,
    speed: float = 1.0,
    smooth: bool = True,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    speed = float(speed)
    if speed <= 0:
        raise ValueError("speed must be greater than 0")

    info = probe_video(input_path, require_video=False)
    vf = _speed_vf(speed, info.fps, smooth)

    if output_path is None:
        output_path = default_output_path(input_path, "speed")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-i", input_path, "-vf", vf]
    if info.has_audio:
        args += ["-af", _atempo_chain(speed), "-c:a", "aac"]
    else:
        args += ["-an"]
    args += [*video_codec_args(lossless), output_path]
    _run_ffmpeg(args)

    new_duration = info.duration / speed
    return {"output_path": output_path, "speed": speed, "smooth": smooth, "new_duration": round(new_duration, 3)}


def speed_ramp(
    input_path: str,
    segments: list[dict],
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    if not segments:
        raise ValueError("segments is empty")

    info = probe_video(input_path, require_video=False)

    if output_path is None:
        output_path = default_output_path(input_path, "ramp")
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
            vf = _speed_vf(speed, info.fps, smooth)
            args = ["-ss", f"{start}", "-i", input_path, "-t", f"{end - start}", "-vf", vf]
            if info.has_audio:
                args += ["-af", _atempo_chain(speed), "-c:a", "aac"]
            else:
                args += ["-an"]
            args += [*video_codec_args(lossless), seg_path]
            _run_ffmpeg(args)
            seg_files.append(seg_path)

        concat_list = os.path.join(tmp, "concat.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for seg in seg_files:
                f.write(f"file '{seg}'\n")
        _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output_path])

    out_info = probe_video(output_path, require_video=False)
    return {"output_path": output_path, "segment_count": len(segments), "duration": round(out_info.duration, 3)}
