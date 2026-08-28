import os

from framewright_core import default_output_path, probe_video, video_codec_args
from framewright_core import run_ffmpeg as _run_ffmpeg

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}


def _is_image(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


def remove_background(
    input_path: str,
    color: str = "0x00FF00",
    similarity: float = 0.18,
    blend: float = 0.05,
    output_path: str | None = None,
) -> dict:
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    probe_video(input_path, require_video=False)
    vf = f"chromakey=color={color}:similarity={similarity}:blend={blend},format=yuva420p"

    if output_path is None:
        output_path = default_output_path(input_path, "keyed", ext=".webm")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = ["-i", input_path, "-vf", vf, "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-an", output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "color": color, "similarity": similarity, "blend": blend}


def replace_background(
    foreground_path: str,
    background_path: str,
    color: str = "0x00FF00",
    similarity: float = 0.18,
    blend: float = 0.05,
    output_path: str | None = None,
    lossless: bool = False,
) -> dict:
    if not os.path.exists(foreground_path):
        raise FileNotFoundError(f"Foreground not found: {foreground_path}")
    if not os.path.exists(background_path):
        raise FileNotFoundError(f"Background not found: {background_path}")

    fg_info = probe_video(foreground_path, require_video=False)
    w, h = fg_info.width, fg_info.height
    duration = fg_info.duration

    input_args = ["-i", foreground_path]
    if _is_image(background_path):
        input_args += ["-loop", "1", "-t", f"{duration}", "-i", background_path]
    else:
        bg_info = probe_video(background_path, require_video=False)
        if bg_info.duration < duration:
            input_args += ["-stream_loop", "-1", "-i", background_path]
        else:
            input_args += ["-i", background_path]

    filter_complex = (
        f"[0:v]chromakey=color={color}:similarity={similarity}:blend={blend},format=yuva420p[fg];"
        f"[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[bg];"
        f"[bg][fg]overlay=shortest=1[vout]"
    )

    if output_path is None:
        output_path = default_output_path(foreground_path, "bg_replaced")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = input_args + ["-filter_complex", filter_complex, "-map", "[vout]"]
    if fg_info.has_audio:
        args += ["-map", "0:a", "-c:a", "aac"]
    args += video_codec_args(lossless) + ["-t", f"{duration}", output_path]
    _run_ffmpeg(args)
    return {"output_path": output_path, "color": color, "similarity": similarity, "blend": blend}
