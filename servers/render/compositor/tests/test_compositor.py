import json
import subprocess

import pytest

np = pytest.importorskip("numpy")
compositor = pytest.importorskip("compositor_mcp.compositor")


def _frame(path, t):
    out = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            str(t),
            "-i",
            path,
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(120, 160, 3).astype(int)


def _streams(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return [s["codec_type"] for s in json.loads(out.stdout)["streams"]]


def test_image_layer_position_and_timing(media, tmp_path):
    out = str(tmp_path / "comp.mp4")
    layer = {"file": media["red"], "x": 10, "y": 10, "start_time": 0.5}
    res = compositor.compose_layers(media["base"], [layer], output_path=out)
    assert res["layer_count"] == 1 and res["duration"] == pytest.approx(1.0, abs=0.05)
    before, after = _frame(out, 0.2), _frame(out, 0.8)
    assert before[30, 30].max() < 40
    assert after[30, 30][0] > 200 and after[30, 30][1] < 60
    assert after[100, 140].max() < 40  # outside the layer stays black


def test_opacity(media, tmp_path):
    out = str(tmp_path / "half.mp4")
    compositor.compose_layers(media["base"], [{"file": media["red"], "opacity": 0.5}], output_path=out)
    assert 90 < _frame(out, 0.5)[20, 20][0] < 170


def test_scaled_layer(media, tmp_path):
    out = str(tmp_path / "scaled.mp4")
    compositor.compose_layers(media["base"], [{"file": media["red"], "width": 80, "height": -1}], output_path=out)
    frame = _frame(out, 0.5)
    assert frame[70, 70][0] > 200 and frame[100, 100].max() < 40


def test_video_layer_audio_is_mixed(media, tmp_path):
    out = str(tmp_path / "mixed.mp4")
    compositor.compose_layers(media["base"], [{"file": media["clip"], "audio": True}], output_path=out)
    assert sorted(_streams(out)) == ["audio", "video"]


def test_bad_layers_raise(media):
    with pytest.raises(ValueError):
        compositor.compose_layers(media["base"], [])
    with pytest.raises(ValueError):
        compositor.compose_layers(media["base"], [{"file": media["red"], "start_time": 0.8, "end_time": 0.5}])
    with pytest.raises(FileNotFoundError):
        compositor.compose_layers(media["base"], [{"file": "nope.png"}])
