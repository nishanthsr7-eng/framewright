import shutil
import subprocess

import pytest

SR = 22050


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    """A 6 s 120 BPM click track and two 3 s test clips."""
    np = pytest.importorskip("numpy")
    sf = pytest.importorskip("soundfile")
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe not on PATH")
    d = tmp_path_factory.mktemp("beat_sync")
    y = np.zeros(SR * 6, dtype=np.float32)
    click = np.sin(2 * np.pi * 1000 * np.arange(int(SR * 0.03)) / SR).astype(np.float32)
    for t in np.arange(0.5, 5.5, 0.5):
        i = int(t * SR)
        y[i : i + click.size] += click
    music = d / "clicks.wav"
    sf.write(music, y, SR)
    clips = []
    for n, pattern in enumerate(("testsrc", "smptebars")):
        clip = d / f"clip{n}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"{pattern}=size=160x120:rate=25:duration=3",
                "-pix_fmt",
                "yuv420p",
                str(clip),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        clips.append(str(clip))
    return {"music": str(music), "clips": clips}
