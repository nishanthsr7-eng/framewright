import os

from framewright_core import default_output_path, probe_video, video_codec_args
from framewright_core import run_ffmpeg as _run_ffmpeg

ASSETS_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "assets")
LIGHT_LEAK_STYLES = {"warm", "golden", "cool", "white"}
PAN_DIRECTIONS = {"left_to_right", "right_to_left", "static"}


def _escape_filter_path(path):
    p = os.path.abspath(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


def add_film_grain(
    input_path: str,
    intensity: int = 20,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    info = probe_video(input_path, require_video=False)
    intensity = max(0, min(100, int(intensity)))

    if output_path is None:
        output_path = default_output_path(input_path, "grain")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    vf = f"noise=alls={intensity}:allf=t+u"
    args = ["-i", input_path, "-vf", vf]
    if info.has_audio:
        args += ["-c:a", "copy"]
    args += (video_codec_args(True) if lossless else []) + [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "intensity": intensity}


def add_vignette(
    input_path: str,
    intensity: float = 0.5,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    info = probe_video(input_path, require_video=False)
    intensity = max(0.0, min(1.0, float(intensity)))

    if output_path is None:
        output_path = default_output_path(input_path, "vignette")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # angle ranges roughly PI/5 (subtle) .. 3PI/5 (strong)
    angle = (3.14159265 / 5.0) + intensity * (3.14159265 * 2.0 / 5.0)
    vf = f"vignette=angle={angle:.5f}"
    args = ["-i", input_path, "-vf", vf]
    if info.has_audio:
        args += ["-c:a", "copy"]
    args += (video_codec_args(True) if lossless else []) + [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "intensity": intensity}


def add_chromatic_aberration(
    input_path: str,
    shift: int = 3,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    info = probe_video(input_path, require_video=False)
    shift = int(shift)

    if output_path is None:
        output_path = default_output_path(input_path, "chroma_ab")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    vf = f"rgbashift=rh={shift}:bh={-shift}"
    args = ["-i", input_path, "-vf", vf]
    if info.has_audio:
        args += ["-c:a", "copy"]
    args += (video_codec_args(True) if lossless else []) + [output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "shift": shift}


def add_light_leak(
    input_path: str,
    style: str = "warm",
    intensity: float = 0.5,
    pan: str = "left_to_right",
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")
    if style not in LIGHT_LEAK_STYLES:
        raise ValueError(f"style must be one of: {', '.join(sorted(LIGHT_LEAK_STYLES))}")
    if pan not in PAN_DIRECTIONS:
        raise ValueError(f"pan must be one of: {', '.join(sorted(PAN_DIRECTIONS))}")

    info = probe_video(input_path, require_video=False)
    intensity = max(0.0, min(1.0, float(intensity)))
    w, h, duration = info.width, info.height, max(info.duration, 0.1)
    asset_path = os.path.join(ASSETS_DIR, f"{style}.png")

    if output_path is None:
        output_path = default_output_path(input_path, "light_leak")
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

    args = ["-i", input_path, "-loop", "1", "-i", asset_path, "-filter_complex", filter_complex, "-map", "[vout]"]
    if info.has_audio:
        args += ["-map", "0:a", "-c:a", "copy"]
    args += [*video_codec_args(lossless), "-t", f"{duration}", output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "style": style, "intensity": intensity, "pan": pan}
