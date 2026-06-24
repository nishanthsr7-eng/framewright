import shutil
import subprocess

import pytest


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True, timeout=60)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """1 s green-screen clip with a red box in the middle, and a solid blue background image."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("chroma")
    fg, bg = d / "green.mp4", d / "blue.png"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=0x00FF00:s=160x120:r=25:d=1",
        "-vf",
        "drawbox=x=60:y=40:w=40:h=40:color=red:t=fill",
        "-pix_fmt",
        "yuv420p",
        str(fg),
    )
    _ffmpeg("-f", "lavfi", "-i", "color=c=blue:s=320x240", "-frames:v", "1", str(bg))
    return {"fg": str(fg), "bg": str(bg)}
