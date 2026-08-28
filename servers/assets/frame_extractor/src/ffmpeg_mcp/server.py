import json
import os
import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

import ffmpeg_mcp.cut_video as cut_video

setup_logging()
mcp = FastMCP("frame-extractor-mcp")

VideoPath = Annotated[str, Field(description="Source video file")]
Time = Annotated[float | str | None, Field(description="Seconds, or 'MM:SS' / 'HH:MM:SS'")]
IMG_FORMATS = {"png": 0, "jpg": 1, "webp": 2}


def _need_file(path: str) -> None:
    if not os.path.isfile(path):
        raise ToolError(f"File not found: {path}. Check the path exists.")


def _check(result: dict, what: str) -> dict:
    """Turn the vendored {code, output_path, log_tail|error} shape into a result or a ToolError."""
    if result.get("code", 0) != 0 or result.get("error"):
        detail = result.get("error") or result.get("log_tail", "")[-600:]
        raise ToolError(f"{what} failed: {detail}")
    return {"output_path": result["output_path"]}


@mcp.tool()
def clip_video(
    video_path: VideoPath,
    start: Time = None,
    end: Time = None,
    duration: Time = None,
    output_path: Annotated[str | None, Field(description="Default: '<video>_clip.<ext>' next to the source")] = None,
) -> dict:
    """Cut a time range out of a video. Give end or duration; start defaults to 0."""
    _need_file(video_path)
    if end is None and duration is not None and start is None:
        start = 0
    try:
        result = cut_video.clip_video_ffmpeg(
            video_path, start=start, end=end, duration=duration, output_path=output_path, time_out=600
        )
    except ValueError as e:
        raise ToolError(f"Bad time value: {e}. Use seconds or 'MM:SS' / 'HH:MM:SS'.") from e
    return _check(result, "Clip")


@mcp.tool()
def concat_videos(
    input_files: Annotated[list[str], Field(min_length=2, description="Videos to join, in order")],
    output_path: Annotated[str | None, Field(description="Output file; its extension sets the container")] = None,
    fast: Annotated[
        bool, Field(description="Stream copy; only when all inputs share codec, size and frame rate")
    ] = False,
) -> dict:
    """Join videos end to end."""
    for f in input_files:
        _need_file(f)
    output_path = output_path or os.path.splitext(input_files[0])[0] + "_concat.mp4"
    code, log = cut_video.concat_videos(input_files, output_path, fast)
    if code != 0:
        hint = " Retry with fast=false." if fast else ""
        raise ToolError(f"Concat failed: {log[-600:]}{hint}")
    return {"output_path": output_path}


@mcp.tool()
def get_video_info(video_path: VideoPath) -> dict:
    """Stream details from ffprobe: codec, width, height, frame rate, duration."""
    _need_file(video_path)
    code, _cmd, log = cut_video.get_video_info(video_path)
    if code != 0:
        raise ToolError(f"ffprobe failed: {log[-600:]}")
    try:
        streams = json.loads(log).get("streams", [])
    except json.JSONDecodeError as e:
        raise ToolError("ffprobe returned unreadable output") from e
    keep = (
        "index",
        "codec_type",
        "codec_name",
        "width",
        "height",
        "r_frame_rate",
        "duration",
        "sample_rate",
        "channels",
        "pix_fmt",
        "bit_rate",
    )
    return {"video_path": video_path, "streams": [{k: s[k] for k in keep if k in s} for s in streams]}


@mcp.tool()
def scale_video(
    video_path: VideoPath,
    width: Annotated[int, Field(gt=0, description="Target width in pixels")],
    height: Annotated[int, Field(description="Target height in pixels; -2 keeps aspect ratio")] = -2,
    output_path: Annotated[str | None, Field(description="Default: next to the source")] = None,
) -> dict:
    """Resize a video."""
    _need_file(video_path)
    if height <= 0 and height != -2:
        raise ToolError("height must be positive, or -2 to keep the aspect ratio")
    return _check(cut_video.scale_video(video_path, width, height, output_path), "Scale")


@mcp.tool()
def extract_frames_from_video(
    video_path: VideoPath,
    every_seconds: Annotated[float, Field(ge=0, description="Grab one frame every N seconds; 0 grabs every frame")] = 0,
    output_folder: Annotated[str | None, Field(description="Default: output/<video>/")] = None,
    format: Annotated[Literal["png", "jpg", "webp"], Field(description="Image format")] = "png",
    max_frames: Annotated[int, Field(ge=0, description="Stop after N frames; 0 means no limit")] = 0,
) -> dict:
    """Save video frames as numbered images (frame_0001.png, ...)."""
    _need_file(video_path)
    result = _check(
        cut_video.extract_frames_from_video(video_path, every_seconds, output_folder, IMG_FORMATS[format], max_frames),
        "Frame extraction",
    )
    folder = os.path.dirname(result["output_path"])
    return {"output_folder": folder, "frame_count": len(os.listdir(folder))}


@mcp.tool()
def enhance_frames(
    input_folder: Annotated[str, Field(description="Folder of frames, e.g. from extract_frames_from_video")],
    style: Annotated[
        Literal["anime", "general"], Field(description="'anime' for animation, 'general' for live-action")
    ] = "general",
    fast: Annotated[bool, Field(description="Anime only: use the faster anime-video model")] = False,
    scale: Annotated[Literal[2, 3, 4], Field(description="Upscale factor")] = 4,
    output_folder: Annotated[str | None, Field(description="Default: '<input_folder>_enhanced'")] = None,
    format: Annotated[Literal["png", "jpg", "webp"], Field(description="Image format")] = "png",
    in_place: Annotated[bool, Field(description="Overwrite the input frames instead of writing a new folder")] = False,
) -> dict:
    """Upscale and clean up frames with Real-ESRGAN. Needs models from scripts/fetch_models.py."""
    if not os.path.isdir(input_folder):
        raise ToolError(f"Folder not found: {input_folder}")
    if style == "anime":
        model = "realesr-animevideov3" if fast else "realesrgan-x4plus-anime"
    else:
        model = "realesrgan-x4plus"
    code, log, out = cut_video.enhance_frames(input_folder, output_folder, model, scale, IMG_FORMATS[format], in_place)
    if code != 0:
        hint = " Run: python scripts/fetch_models.py realesrgan" if "RealESRGAN" in log else ""
        raise ToolError(f"Enhance failed: {log.strip()[-600:]}{hint}")
    return {"output_folder": out, "model": model, "scale": scale}


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
