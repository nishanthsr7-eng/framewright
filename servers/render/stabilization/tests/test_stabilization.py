import json
import subprocess

import pytest

np = pytest.importorskip("numpy")
stabilize = pytest.importorskip("stabilization_mcp.stabilize")


def _frames(path):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(-1, 120, 160).astype(float)


def _jitter(path):
    f = _frames(path)[:, 20:-20, 20:-20]
    return float(np.abs(np.diff(f, axis=0)).mean())


def test_stabilize_reduces_jitter(shaky, tmp_path):
    out = str(tmp_path / "stable.mp4")
    res = stabilize.stabilize_video(shaky, smoothing=15, shakiness=10, output_path=out)
    assert res == {"output_path": out, "smoothing": 15, "shakiness": 10, "zoom": 0}
    assert _jitter(out) < _jitter(shaky)
    streams = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", out],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )["streams"]
    assert {s["codec_type"] for s in streams} == {"video", "audio"}


def test_shakiness_is_clamped(shaky, tmp_path):
    res = stabilize.stabilize_video(shaky, shakiness=50, output_path=str(tmp_path / "x.mp4"))
    assert res["shakiness"] == 10


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        stabilize.stabilize_video(str(tmp_path / "nope.mp4"))
