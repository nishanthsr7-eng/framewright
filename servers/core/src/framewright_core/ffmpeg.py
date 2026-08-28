import json
import subprocess
from dataclasses import dataclass


def run_ffmpeg(args: list[str], timeout: float = 1800, cwd: str | None = None) -> str:
    """Run `ffmpeg -y <args>`. Raises RuntimeError with the stderr tail on failure; returns stderr."""
    cmd = ["ffmpeg", "-y"] + list(args)
    # stdin=DEVNULL: under MCP, stdin is the protocol pipe; an inherited one makes ffmpeg block.
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1500:]}")
    return result.stderr


def video_codec_args(lossless: bool = False) -> list[str]:
    """H.264 encode args. lossless=True writes a qp-0 intermediate so chained tools don't stack re-encode loss."""
    if lossless:
        return ["-c:v", "libx264", "-preset", "ultrafast", "-qp", "0", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p"]


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool
    has_video: bool = True


def probe_video(path: str, require_video: bool = True, timeout: float = 60) -> VideoInfo:
    """ffprobe a media file. With require_video=False, audio-only files return width/height 0 and has_video False.

    fps falls back to 30.0 when the stream reports none. Raises RuntimeError if ffprobe fails.
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_type,width,height,r_frame_rate,duration:format=duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}: {result.stderr[-500:]}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None and require_video:
        raise RuntimeError(f"No video stream in {path}")
    fps = 30.0
    if video:
        num, _, den = video.get("r_frame_rate", "").partition("/")
        try:
            fps = float(num) / float(den or 1) or 30.0
        except (ValueError, ZeroDivisionError):
            pass
    duration = data.get("format", {}).get("duration") or (video or {}).get("duration") or 0.0
    return VideoInfo(
        width=int(video.get("width", 0)) if video else 0,
        height=int(video.get("height", 0)) if video else 0,
        duration=float(duration),
        fps=fps,
        has_audio=any(s.get("codec_type") == "audio" for s in streams),
        has_video=video is not None,
    )
