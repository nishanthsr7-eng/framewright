import os

from framewright_core import default_output_path, video_codec_args
from framewright_core import run_ffmpeg as _run_ffmpeg

PAN_DIRECTIONS = {
    "center",
    "left_to_right",
    "right_to_left",
    "top_to_bottom",
    "bottom_to_top",
}


def create_ken_burns(
    image_path: str,
    duration: float = 5.0,
    zoom_start: float = 1.0,
    zoom_end: float = 1.3,
    pan: str = "center",
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    if pan not in PAN_DIRECTIONS:
        raise ValueError(f"pan must be one of: {', '.join(sorted(PAN_DIRECTIONS))}")

    duration = float(duration)
    fps = int(fps)
    d = max(2, int(round(duration * fps)))

    z_expr = f"{zoom_start}+({zoom_end}-{zoom_start})*on/{d - 1}"

    if pan == "left_to_right":
        x_expr = f"(iw-iw/zoom)*(on/{d - 1})"
    elif pan == "right_to_left":
        x_expr = f"(iw-iw/zoom)*(1-on/{d - 1})"
    else:
        x_expr = "(iw-iw/zoom)/2"

    if pan == "top_to_bottom":
        y_expr = f"(ih-ih/zoom)*(on/{d - 1})"
    elif pan == "bottom_to_top":
        y_expr = f"(ih-ih/zoom)*(1-on/{d - 1})"
    else:
        y_expr = "(ih-ih/zoom)/2"

    vf = (
        f"scale=3840:-2,"
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={d}:s={width}x{height}:fps={fps},"
        f"format=yuv420p"
    )

    if output_path is None:
        output_path = default_output_path(image_path, "ken_burns", ext=".mp4")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = [
        "-loop",
        "1",
        "-i",
        image_path,
        "-vf",
        vf,
        "-t",
        f"{duration}",
        *video_codec_args(lossless),
        output_path,
    ]
    _run_ffmpeg(args)

    return {
        "output_path": output_path,
        "duration": duration,
        "zoom_start": zoom_start,
        "zoom_end": zoom_end,
        "pan": pan,
        "width": width,
        "height": height,
        "fps": fps,
    }
