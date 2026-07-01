import shutil
import subprocess

import pytest


def _make(path, vf):
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=160x120:rate=25:duration=1",
            "-f",
            "lavfi",
            "-i",
            "sine=duration=1",
            "-shortest",
            "-vf",
            vf,
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return str(path)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """The same test pattern twice: untouched, and darkened with a blue cast."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("color")
    return {
        "plain": _make(d / "plain.mp4", "null"),
        "moody": _make(d / "moody.mp4", "lutrgb=r=val*0.4:g=val*0.5:b=val*0.8+30"),
    }
