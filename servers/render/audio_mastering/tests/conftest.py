import shutil
import subprocess

import pytest


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True, capture_output=True, timeout=60)


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """Quiet tone, low hiss, music bed, and 2 s clips with and without audio."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("mastering")
    quiet, noisy, music = d / "quiet.wav", d / "noisy.wav", d / "music.wav"
    av, v = d / "av.mp4", d / "v.mp4"
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=4", "-af", "volume=0.03", str(quiet))
    _ffmpeg("-f", "lavfi", "-i", "anoisesrc=color=white:amplitude=0.003:duration=3", str(noisy))
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=220:duration=1", str(music))
    _ffmpeg(
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=160x120:rate=25:duration=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=880:duration=2",
        "-shortest",
        "-pix_fmt",
        "yuv420p",
        str(av),
    )
    _ffmpeg("-f", "lavfi", "-i", "testsrc=size=160x120:rate=25:duration=2", "-pix_fmt", "yuv420p", str(v))
    return {k: str(p) for k, p in {"quiet": quiet, "noisy": noisy, "music": music, "av": av, "v": v}.items()}
