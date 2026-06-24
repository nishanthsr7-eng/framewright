import shutil
import subprocess

import pytest


@pytest.fixture(scope="session")
def clip(tmp_path_factory):
    """2 s 320x240 test clip at 25 fps (50 frames). The folder has a space to exercise quoting."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("frame extractor")
    path = d / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x240:rate=25:duration=2",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return str(path)
