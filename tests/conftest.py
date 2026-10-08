import shutil
import subprocess

import pytest

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _lavfi(path, seconds, size="320x240", rate=25, audio=True):
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={size}:rate={rate}:duration={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest"]
    args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, capture_output=True, timeout=60)
    return str(path)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """Tiny lavfi clips: 2 s with audio, 1 s without audio."""
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("media")
    return {
        "av": _lavfi(d / "av.mp4", 2),
        "v": _lavfi(d / "v.mp4", 1, audio=False),
        "dir": d,
    }
