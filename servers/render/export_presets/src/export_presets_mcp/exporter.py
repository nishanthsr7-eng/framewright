import json
import os
import subprocess

from framewright_core import output_root as _get_output_root
from framewright_core import run_ffmpeg as _run_ffmpeg


def _probe(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr[-1000:]}")
    data = json.loads(result.stdout)
    vstream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if vstream is None:
        raise RuntimeError(f"No video stream in: {video_path}")
    has_audio = any(s["codec_type"] == "audio" for s in data["streams"])
    num, den = (vstream.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    fps = float(num) / float(den) if float(den) != 0 else 30.0
    return {
        "width": int(vstream["width"]), "height": int(vstream["height"]),
        "fps": fps, "has_audio": has_audio,
    }


PRESETS = {
    "youtube": {
        "width": 1920, "height": 1080, "aspect": "16:9",
        "video_bitrate": "12M", "audio_bitrate": "192k", "fps_max": 60,
        "description": "YouTube landscape 1080p",
    },
    "youtube_shorts": {
        "width": 1080, "height": 1920, "aspect": "9:16",
        "video_bitrate": "10M", "audio_bitrate": "128k", "fps_max": 60,
        "description": "YouTube Shorts vertical",
    },
    "tiktok": {
        "width": 1080, "height": 1920, "aspect": "9:16",
        "video_bitrate": "10M", "audio_bitrate": "128k", "fps_max": 60,
        "description": "TikTok vertical",
    },
    "instagram_reels": {
        "width": 1080, "height": 1920, "aspect": "9:16",
        "video_bitrate": "10M", "audio_bitrate": "128k", "fps_max": 60,
        "description": "Instagram Reels vertical",
    },
    "instagram_post": {
        "width": 1080, "height": 1080, "aspect": "1:1",
        "video_bitrate": "8M", "audio_bitrate": "128k", "fps_max": 30,
        "description": "Instagram feed post, square",
    },
    "instagram_story": {
        "width": 1080, "height": 1920, "aspect": "9:16",
        "video_bitrate": "10M", "audio_bitrate": "128k", "fps_max": 30,
        "description": "Instagram Story vertical",
    },
    "twitter": {
        "width": 1280, "height": 720, "aspect": "16:9",
        "video_bitrate": "5M", "audio_bitrate": "128k", "fps_max": 40,
        "description": "Twitter/X landscape 720p",
    },
    "facebook": {
        "width": 1280, "height": 720, "aspect": "16:9",
        "video_bitrate": "8M", "audio_bitrate": "128k", "fps_max": 30,
        "description": "Facebook landscape 720p",
    },
}


def list_platform_presets():
    return PRESETS


def _default_output_path(video_path, platform):
    base, ext = os.path.splitext(os.path.basename(video_path))
    out_dir = os.path.join(_get_output_root(), base)
    os.makedirs(out_dir, exist_ok=True)
    return os.path.join(out_dir, f"{base}_{platform}{ext if ext else '.mp4'}")


def export_for_platform(video_path, platform, output_path=None, fit_mode="crop"):
    """
    按指定社交平台的推荐分辨率/码率/帧率导出视频。

    fit_mode:
      - "crop" (默认): 缩放至覆盖目标尺寸后居中裁切，画面填满目标比例，
        可能裁掉边缘内容。
      - "pad": 缩放至适应目标尺寸后用黑边填充，保留完整画面但可能有黑边。
    """
    if platform not in PRESETS:
        raise ValueError(f"Unknown platform: {platform}. Available: {list(PRESETS.keys())}")
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File not found: {video_path}")

    preset = PRESETS[platform]
    tw, th = preset["width"], preset["height"]
    info = _probe(video_path)

    if fit_mode == "pad":
        vf = (
            f"scale={tw}:{th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black"
        )
    elif fit_mode == "crop":
        vf = (
            f"scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th}"
        )
    else:
        raise ValueError("fit_mode must be 'crop' or 'pad'")

    if info["fps"] > preset["fps_max"]:
        vf += f",fps={preset['fps_max']}"

    if output_path is None:
        output_path = _default_output_path(video_path, platform)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = [
        "-i", video_path, "-vf", vf,
        "-c:v", "libx264", "-b:v", preset["video_bitrate"], "-preset", "medium",
        "-pix_fmt", "yuv420p",
    ]
    if info["has_audio"]:
        args += ["-c:a", "aac", "-b:a", preset["audio_bitrate"]]
    else:
        args += ["-an"]
    args += [output_path]

    _run_ffmpeg(args)
    return {"output_path": output_path, "platform": platform, "width": tw, "height": th, "fit_mode": fit_mode}
