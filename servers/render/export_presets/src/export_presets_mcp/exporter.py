import os

from framewright_core import default_output_path, probe_video
from framewright_core import run_ffmpeg as _run_ffmpeg

PRESETS = {
    "youtube": {
        "width": 1920,
        "height": 1080,
        "aspect": "16:9",
        "video_bitrate": "12M",
        "audio_bitrate": "192k",
        "fps_max": 60,
        "description": "YouTube landscape 1080p",
    },
    "youtube_shorts": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "video_bitrate": "10M",
        "audio_bitrate": "128k",
        "fps_max": 60,
        "description": "YouTube Shorts vertical",
    },
    "tiktok": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "video_bitrate": "10M",
        "audio_bitrate": "128k",
        "fps_max": 60,
        "description": "TikTok vertical",
    },
    "instagram_reels": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "video_bitrate": "10M",
        "audio_bitrate": "128k",
        "fps_max": 60,
        "description": "Instagram Reels vertical",
    },
    "instagram_post": {
        "width": 1080,
        "height": 1080,
        "aspect": "1:1",
        "video_bitrate": "8M",
        "audio_bitrate": "128k",
        "fps_max": 30,
        "description": "Instagram feed post, square",
    },
    "instagram_story": {
        "width": 1080,
        "height": 1920,
        "aspect": "9:16",
        "video_bitrate": "10M",
        "audio_bitrate": "128k",
        "fps_max": 30,
        "description": "Instagram Story vertical",
    },
    "twitter": {
        "width": 1280,
        "height": 720,
        "aspect": "16:9",
        "video_bitrate": "5M",
        "audio_bitrate": "128k",
        "fps_max": 40,
        "description": "Twitter/X landscape 720p",
    },
    "facebook": {
        "width": 1280,
        "height": 720,
        "aspect": "16:9",
        "video_bitrate": "8M",
        "audio_bitrate": "128k",
        "fps_max": 30,
        "description": "Facebook landscape 720p",
    },
}


def list_platform_presets() -> dict:
    return PRESETS


def export_for_platform(
    video_path: str,
    platform: str,
    output_path: str | None = None,
    fit_mode: str = "crop",
) -> dict:
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
    info = probe_video(video_path)

    if fit_mode == "pad":
        vf = f"scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black"
    elif fit_mode == "crop":
        vf = f"scale={tw}:{th}:force_original_aspect_ratio=increase,crop={tw}:{th}"
    else:
        raise ValueError("fit_mode must be 'crop' or 'pad'")

    if info.fps > preset["fps_max"]:
        vf += f",fps={preset['fps_max']}"

    if output_path is None:
        output_path = default_output_path(video_path, platform)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    args = [
        "-i",
        video_path,
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-b:v",
        preset["video_bitrate"],
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
    ]
    if info.has_audio:
        args += ["-c:a", "aac", "-b:a", preset["audio_bitrate"]]
    else:
        args += ["-an"]
    args += [output_path]

    _run_ffmpeg(args)
    return {"output_path": output_path, "platform": platform, "width": tw, "height": th, "fit_mode": fit_mode}
