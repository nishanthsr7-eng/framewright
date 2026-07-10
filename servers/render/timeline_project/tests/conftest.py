import shutil
import subprocess

import pytest


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True, timeout=60)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """Two 2 s clips of different sizes (one with audio), a still image and a small logo."""
    Image = pytest.importorskip("PIL.Image")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("timeline")
    a, b, still, logo = d / "a.mp4", d / "b.mp4", d / "still.png", d / "logo.png"
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x180:rate=25:duration=2",
        "-f",
        "lavfi",
        "-i",
        "sine=duration=2",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(a),
    )
    _ffmpeg("-f", "lavfi", "-i", "smptebars=size=200x200:rate=30:duration=2", "-pix_fmt", "yuv420p", str(b))
    Image.new("RGB", (100, 60), "blue").save(still)
    Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(logo)
    return {"a": str(a), "b": str(b), "still": str(still), "logo": str(logo)}


@pytest.fixture
def project(tmp_path):
    return str(tmp_path / "edit.json")
