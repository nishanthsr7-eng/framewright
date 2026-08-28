import os
import tempfile
from functools import partial

from framewright_core import default_output_path, probe_video, run_ffmpeg, video_codec_args

_run_ffmpeg = partial(run_ffmpeg, timeout=3600)


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def stabilize_video(
    input_path: str,
    smoothing: int = 10,
    shakiness: int = 5,
    zoom: int = 0,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    info = probe_video(input_path, require_video=False)
    shakiness = max(1, min(10, int(shakiness)))
    smoothing = max(0, int(smoothing))

    if output_path is None:
        output_path = default_output_path(input_path, "stabilized")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        trf_path = os.path.join(tmp, "transforms.trf")
        trf_escaped = _escape_filter_path(trf_path)

        # Pass 1: analyze motion
        _run_ffmpeg(
            [
                "-i",
                input_path,
                "-vf",
                f"vidstabdetect=shakiness={shakiness}:accuracy=15:result='{trf_escaped}'",
                "-f",
                "null",
                "-",
            ]
        )

        # Pass 2: apply stabilizing transform
        vf = f"vidstabtransform=input='{trf_escaped}':zoom={zoom}:smoothing={smoothing},unsharp=5:5:0.8:3:3:0.4"
        args = ["-i", input_path, "-vf", vf, *video_codec_args(lossless)]
        if info.has_audio:
            args += ["-c:a", "copy"]
        args += (video_codec_args(True) if lossless else []) + [output_path]
        _run_ffmpeg(args)

    return {"output_path": output_path, "smoothing": smoothing, "shakiness": shakiness, "zoom": zoom}
