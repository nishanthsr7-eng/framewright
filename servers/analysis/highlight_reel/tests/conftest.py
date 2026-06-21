import shutil
import subprocess

import pytest


def _make(path, seconds, audio_expr=None):
    args = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=160x120:rate=25:duration={seconds}"]
    if audio_expr:
        args += ["-f", "lavfi", "-i", f"aevalsrc='{audio_expr}':s=22050:d={seconds}", "-shortest"]
    args += ["-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, capture_output=True, timeout=60)
    return str(path)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """12 s clip that is quiet except for a loud burst at 6-8 s, plus a silent-track-free clip."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("highlights")
    loud = "if(between(t,6,8),0.9,0.01)*sin(2*PI*440*t)"
    return {
        "burst": _make(d / "burst.mp4", 12, loud),
        "no_audio": _make(d / "no_audio.mp4", 6),
    }
