import shutil
import subprocess

import pytest


def _make(path, seconds, audio=True):
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=160x120:rate=25:duration={seconds}"]
    if audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-shortest"]
    args += ["-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, capture_output=True, timeout=60)
    return str(path)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """Tiny lavfi clips: 1 s with audio, 1 s without audio."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("media")
    return {"av": _make(d / "av.mp4", 1), "v": _make(d / "v.mp4", 1, audio=False)}
