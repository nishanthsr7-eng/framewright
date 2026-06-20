import shutil
import subprocess

import pytest


@pytest.fixture(scope="session")
def three_shots(tmp_path_factory):
    """3 s video with hard cuts at 1 s and 2 s (red, green, blue)."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not on PATH")
    path = tmp_path_factory.mktemp("scenes") / "shots.mp4"
    args = ["ffmpeg", "-v", "error", "-y"]
    for color in ("red", "green", "blue"):
        args += ["-f", "lavfi", "-i", f"color=c={color}:s=160x120:r=25:d=1"]
    args += ["-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, capture_output=True, timeout=60)
    return str(path)
