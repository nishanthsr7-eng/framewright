import shutil
import subprocess

import pytest


def _make(path, rate, audio=True):
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=320x180:rate={rate}:duration=0.5"]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=duration=0.5", "-shortest"]
    args += ["-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, capture_output=True, timeout=60)
    return str(path)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """Short 16:9 clips: 25 fps with audio, and 60 fps without audio."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("export")
    return {"av": _make(d / "av.mp4", 25), "v60": _make(d / "v60.mp4", 60, audio=False)}
