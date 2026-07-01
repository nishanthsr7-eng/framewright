import shutil
import subprocess

import pytest


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True, timeout=60)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """1 s black base with audio, a red 40x40 PNG, and a 1 s clip with its own audio."""
    Image = pytest.importorskip("PIL.Image")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("compositor")
    base, clip, red = d / "base.mp4", d / "clip.mp4", d / "red.png"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=160x120:r=25:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=duration=1",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(base),
    )
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=80x60:rate=25:duration=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=1",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(clip),
    )
    Image.new("RGBA", (40, 40), (255, 0, 0, 255)).save(red)
    return {"base": str(base), "clip": str(clip), "red": str(red)}
