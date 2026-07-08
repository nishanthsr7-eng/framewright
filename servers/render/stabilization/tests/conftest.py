import shutil
import subprocess

import pytest


def _has_vidstab():
    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30)
    return "vidstabdetect" in out.stdout


@pytest.fixture(scope="session")
def shaky(tmp_path_factory):
    """2 s test pattern with a jittering crop window, plus audio."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    if not _has_vidstab():
        pytest.skip("ffmpeg built without vid.stab")
    path = tmp_path_factory.mktemp("stabilization") / "shaky.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=200x150:rate=25:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=2",
            "-shortest",
            "-vf",
            "crop=160:120:20+12*sin(n*1.7):15+10*cos(n*2.3)",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return str(path)
