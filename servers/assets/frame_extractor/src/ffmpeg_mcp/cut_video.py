import logging
import os
import shlex
import shutil
import tempfile
from enum import Enum

from framewright_core import output_root as _get_output_root
from framewright_core import servers_dir as _find_tools_dir

import ffmpeg_mcp.ffmpeg as ffmpeg
import ffmpeg_mcp.utils as utils

logger = logging.getLogger(__name__)


def enhance_frames(input_folder, output_folder=None, model="realesrgan-x4plus", scale=4, format=0, in_place=False):
    """Upscale image frames with Real-ESRGAN (ncnn-vulkan).

    input_folder: folder of frames (usually from extract_frames_from_video).
    output_folder: default "<input_folder>_enhanced".
    model: realesrgan-x4plus-anime (anime), realesrgan-x4plus (general),
        or realesr-animevideov3 (anime video, faster).
    scale: 2, 3 or 4. format: 0 png, 1 jpg, 2 webp.
    in_place: replace the input frames (output_folder is ignored).
    Returns (code, log, output_folder).
    """
    tools_dir = _find_tools_dir()
    if tools_dir is None:
        return -1, "Could not find the repo's servers/ folder to locate RealESRGAN", ""

    esrgan_dir = os.path.join(os.path.dirname(tools_dir), "models", "realesrgan")
    exe_name = "realesrgan-ncnn-vulkan.exe" if os.name == "nt" else "realesrgan-ncnn-vulkan"
    exe_path = os.path.join(esrgan_dir, exe_name)
    models_dir = os.path.join(esrgan_dir, "models")
    if not os.path.isfile(exe_path):
        return -1, f"RealESRGAN binary not found: {exe_path}", ""
    if not os.path.isdir(input_folder):
        return -1, f"Input folder not found: {input_folder}", ""

    temp_dir = None
    if in_place:
        temp_dir = tempfile.mkdtemp(prefix="esrgan_", dir=input_folder)
        output_folder = temp_dir
    elif output_folder is None:
        output_folder = f"{input_folder.rstrip(os.sep).rstrip('/')}_enhanced"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    img_ext_map = {0: "png", 1: "jpg", 2: "webp"}
    img_ext = img_ext_map.get(format, "png")

    model_name = model
    if model_name.startswith("realesr-animevideov3"):
        model_name = f"realesr-animevideov3-x{scale}"

    cmd = (
        f"{shlex.quote(exe_path)} -i {shlex.quote(input_folder)} "
        f"-o {shlex.quote(output_folder)} -m {shlex.quote(models_dir)} "
        f"-n {shlex.quote(model_name)} -s {scale} -f {img_ext}"
    )
    code, log, append_msg = ffmpeg.run_command(cmd, timeout=3600)

    if in_place:
        if code == 0:
            for name in os.listdir(temp_dir):
                src = os.path.join(temp_dir, name)
                stem = os.path.splitext(name)[0]
                for old_ext in (".png", ".jpg", ".jpeg", ".webp"):
                    old_file = os.path.join(input_folder, stem + old_ext)
                    if os.path.exists(old_file):
                        os.remove(old_file)
                shutil.move(src, os.path.join(input_folder, name))
        shutil.rmtree(temp_dir, ignore_errors=True)
        output_folder = input_folder

    return code, log + "\n" + append_msg, output_folder


def clip_video_ffmpeg(video_path, start=None, end=None, duration=None, output_path=None, time_out=30):
    """Cut a time range from a video.

    start/end/duration: seconds, 'MM:SS' or 'HH:MM:SS'. Give end or duration; start defaults to the beginning.
    output_path: default "<video>_clip.<ext>". time_out: command timeout in seconds.
    Returns {"code", "output_path", "log_tail"} or {"code": -1, "error"}.
    Example: clip_video_ffmpeg("input.mp4", "00:01:30", "02:30")
    """
    try:
        base, ext = os.path.splitext(video_path)
        if output_path is None:
            output_path = f"{base}_clip{ext}"
        cmd = f"-i {shlex.quote(video_path)} "
        if start is not None:
            start_sec = utils.convert_to_seconds(start)
            cmd = f"{cmd} -ss {start_sec}"
        if end is None and duration is not None:
            end = start_sec + utils.convert_to_seconds(duration)
        if end is not None:
            end_sec = utils.convert_to_seconds(end)
            cmd = f"{cmd} -to {end_sec}"
        cmd = f"{cmd} -y {shlex.quote(output_path)}"
        logger.debug("ffmpeg %s", cmd)
        status_code, log = ffmpeg.run_ffmpeg(cmd, timeout=time_out)
        logger.debug(log)
        return {"code": status_code, "output_path": output_path, "log_tail": log[-1500:]}
    except Exception as e:
        logger.error("Clip failed: %s", e)
        return {"code": -1, "output_path": "", "error": str(e)}


def concat_videos(input_files: list[str], output_path: str = None, fast: bool = True):
    """Join videos end to end.

    fast=True stream-copies with the concat demuxer; all inputs must share codec, size and frame rate.
    fast=False re-encodes with the concat filter, scaling/padding later inputs to the first one's size.
    The output container follows the output_path extension (.mp4, .mkv, ...).
    Returns (code, log).
    """
    if output_path is None:
        base, ext = os.path.splitext(input_files[0])
        output_path = f"{base}_clip.mp4"
    # Check that every input exists.
    for file in input_files:
        if not os.path.exists(file):
            raise FileNotFoundError(f"Input file not found: {file}")
    if fast:
        try:
            # Write the concat demuxer's file list.
            temp_list_file = utils.create_temp_file()
            with open(temp_list_file, "w", encoding="utf-8") as f:
                for file in input_files:
                    abs_path = os.path.abspath(file)
                    if os.name == "nt":
                        f.write(f"file '{abs_path}'\n")
                    else:
                        f.write(f"file '{abs_path}'\n")

            # Build the ffmpeg command.
            cmd = f"-f concat -safe 0 -i {shlex.quote(temp_list_file)} -c copy -y {shlex.quote(output_path)}"
            return ffmpeg.run_ffmpeg(cmd)
        finally:
            # Remove the temp list file.
            if os.path.exists(temp_list_file):
                os.remove(temp_list_file)

    elif not fast:
        inputs = []
        filter_str = ""
        fmt_ctx = ffmpeg.media_format_ctx(input_files[0])
        if fmt_ctx is None:
            return -1, f"{input_files[0]}: could not read the video"
        map = ""
        if len(fmt_ctx.video_streams) > 0:  # video (+ audio)
            width = fmt_ctx.video_streams[0].width
            height = fmt_ctx.video_streams[0].height
            aspect = float(width) / float(height)
            for i, file in enumerate(input_files):
                inputs.extend(["-i", shlex.quote(file)])
                if i == 0:
                    filter_str += f"[{i}:v]setsar=1[{i}v];"
                if i > 0:
                    tmp_fmt_ctx = ffmpeg.media_format_ctx(file)
                    if tmp_fmt_ctx is None:
                        return -1, f"{input_files[i]}: could not read the video"
                    if len(tmp_fmt_ctx.video_streams) == 0:
                        return -1, f"{input_files[i]}: no video stream"
                    tmp_width = tmp_fmt_ctx.video_streams[0].width
                    tmp_height = tmp_fmt_ctx.video_streams[0].height
                    tmp_aspect = float(tmp_width) / float(tmp_height)
                    if tmp_width == width and tmp_height == height:
                        filter_str += f"[{i}:v]setsar=1[{i}v];"
                    elif tmp_aspect == aspect:
                        filter_str += f"[{i}:v]scale={width}:{height},setsar=1[{i}v];"
                    elif abs(tmp_aspect - aspect) < 0.15:  # close aspect: scale up and crop
                        filter_str += f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=increase,setsar=1,crop=x=(iw-{width})/2:y=({height}-ih)/2:w={width}:h={height},setsar=1[{i}v];"
                    else:
                        filter_str += f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,setsar=1,pad={width}:{height}:({width}-iw)/2:({height}-ih)/2,setsar=1[{i}v];"
            for i, file in enumerate(input_files):
                if len(fmt_ctx.audio_streams) > 0:
                    filter_str += f"[{i}v][{i}:a]"
                else:
                    filter_str += f"[{i}v]"
            a = 0
            map = " -map '[outv]' "
            out = "[outv]"
            if len(fmt_ctx.audio_streams) > 0:
                a = 1
                map = " -map '[outv]' -map '[outa]' "
                out = "[outv][outa]"
            filter_str += f"concat=n={len(input_files)}:v=1:a={a}{out}"
        elif len(fmt_ctx.audio_streams) > 0:  # audio only
            for i, file in enumerate(input_files):
                inputs.extend(["-i", shlex.quote(file)])
            filter_str += f"concat=n={len(input_files)}:a=1:v=0[outa]"
            map = " -map '[outa]' "

        if len(filter_str) == 0:
            return -1, f"{input_files[0]}: no audio or video streams"
        # Build the inputs and the filter graph.
        inputs_str = " ".join(inputs)
        cmd = f" {inputs_str} -lavfi '{filter_str}' {map} -y {shlex.quote(output_path)}"
        return ffmpeg.run_ffmpeg(cmd)


def get_video_info(video_path: str):
    cmd = f" -v error -show_streams -of json -i {shlex.quote(video_path)}"
    return ffmpeg.run_ffprobe(cmd, timeout=60)


def video_play(video_path: str, speed, loop):
    speed = float(speed)
    loop = int(loop)
    cmd = f" -loop {loop} "
    if loop != 0:
        cmd = f" {cmd} -autoexit"
    audio_filter_str = ""
    video_filter_str = ""
    if speed != 1:
        fmt_ctx = ffmpeg.media_format_ctx(video_path)
        if len(fmt_ctx.audio_streams) > 0:
            audio_filter_str = f"-af atempo={speed}"
        if len(fmt_ctx.video_streams) > 0:
            video_filter_str = f"-vf setpts={1 / speed}*PTS"
    cmd = f" {cmd} {audio_filter_str} {video_filter_str}   -i {shlex.quote(video_path)}"
    logger.debug("ffmpeg %s", cmd)
    return ffmpeg.run_ffplay(cmd, timeout=60)


class Position(Enum):
    TopLeft = (1,)
    TopCenter = (2,)
    TopRight = (3,)
    RightCenter = (4,)
    BottomRight = (5,)
    BottomCenter = (6,)
    BottomLeft = (7,)
    LeftCenter = (8,)
    Center = 9


def overlay_video(background_video, overlay_video, output_path: str = None, position: int = 1, dx=0, dy=0):
    """Picture-in-picture: draw overlay_video on top of background_video (not a concat).

    position: 1 TopLeft, 2 TopCenter, 3 TopRight, 4 RightCenter, 5 BottomRight,
        6 BottomCenter, 7 BottomLeft, 8 LeftCenter, 9 Center.
    dx, dy: pixel offset from that anchor.
    """
    try:
        base, ext = os.path.splitext(background_video)
        if output_path is None:
            if ext is None or len(ext) == 0:
                ext = ".mp4"
            output_path = f"{base}_clip{ext}"
        x = ""
        y = ""
        if position == 1:
            x = f"{dx}"
            y = f"{dy}"
        elif position == Position.LeftCenter:
            x = f"{dx}"
            y = f"(H-h)/2+{dy}"
        elif position == 7:
            x = f"{dx}"
            y = f"(H-h)+{dy}"
        elif position == 6:
            x = f"(W-w)/2+{dx}"
            y = f"(H-h)+{dy}"
        elif position == 5:
            x = f"(W-w)+{dx}"
            y = f"(H-h)+{dy}"
        elif position == 4:
            x = f"(W-w)+{dx}"
            y = f"(H-h)/2+{dy}"
        elif position == 3:
            x = f"(W-w)+{dx}"
            y = f"{dy}"
        elif position == 2:
            x = f"(W-w)/2+{dx}"
            y = f"{dy}"
        elif position == 9:
            x = f"(W-w)/2+{dx}"
            y = f"(H-h)/2+{dy}"

        cmd = f" -i {shlex.quote(background_video)} -i {shlex.quote(overlay_video)} -filter_complex \"[0:v][1:v]overlay=x={x}:y={y}[ov];[0:a][1:a]amix=inputs=2:weights='3 1'[oa]\" -map '[ov]' -map '[oa]'"
        cmd = f"{cmd} -y {shlex.quote(output_path)}"
        logger.debug("ffmpeg %s", cmd)
        status_code, log = ffmpeg.run_ffmpeg(cmd, timeout=1000)
        logger.debug(log)
        return {"code": status_code, "output_path": output_path, "log_tail": log[-1500:]}
    except Exception as e:
        logger.error("Clip failed: %s", e)
        return {"code": -1, "output_path": "", "error": str(e)}


def scale_video(video_path, width, height=-2, output_path: str = None):
    """Resize a video. width/height: pixels; -2 keeps the aspect ratio (rounded to an even number)."""
    try:
        base, ext = os.path.splitext(video_path)
        if output_path is None:
            if ext is None or len(ext) == 0:
                ext = ".mp4"
            output_path = f"{base}_clip{ext}"

        cmd = f' -i {shlex.quote(video_path)} -filter_complex "scale={width}:{height}"'
        cmd = f"{cmd} -y {shlex.quote(output_path)}"
        logger.debug("ffmpeg %s", cmd)
        status_code, log = ffmpeg.run_ffmpeg(cmd, timeout=1000)
        logger.debug(log)
        return {"code": status_code, "output_path": output_path, "log_tail": log[-1500:]}
    except Exception as e:
        logger.error("Clip failed: %s", e)
        return {"code": -1, "output_path": "", "error": str(e)}


def extract_frames_from_video(video_path, fps=0, output_folder=None, format=0, total_frames=0):
    """Save video frames as numbered images.

    fps: grab one frame every N seconds; 0 grabs every frame.
    output_folder: default output/<video name>/. format: 0 png, 1 jpg, 2 webp.
    total_frames: stop after N frames; 0 means no limit.
    """
    # Make sure the output folder exists.
    if output_folder is None:
        # Default: output/<video name>/ at the repo root.
        anime_name = os.path.splitext(os.path.basename(video_path))[0]
        output_folder = os.path.join(_get_output_root(), anime_name)
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    img_ext = "png"
    if format == 0:
        img_ext = "png"
    elif format == 1:
        img_ext = "jpg"
    else:
        img_ext = "webp"
    output_path = os.path.join(output_folder, f"frame_%04d.{img_ext}")
    try:
        cmd = f" -i {shlex.quote(video_path)}"
        # Run ffmpeg.
        if fps > 0:
            cmd = f" {cmd} -vf 'fps=1/{fps}'"
        else:
            cmd = f" {cmd} -vsync 0"
        if total_frames > 0:
            cmd = f" {cmd} -vframes {total_frames} "
        cmd = f" {cmd} -y {shlex.quote(output_path)}"
        status_code, log = ffmpeg.run_ffmpeg(cmd, timeout=1000)
        logger.debug(log)
        return {"code": status_code, "output_path": output_path, "log_tail": log[-1500:]}
    except Exception as e:
        logger.error("Frame extraction failed: %s", e)
        return {"code": -1, "output_path": "", "error": str(e)}
