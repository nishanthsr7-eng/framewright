import json
import subprocess

import pytest

np = pytest.importorskip("numpy")
ken_burns = pytest.importorskip("ken_burns_mcp.ken_burns")


def _frames(path, w, h):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(-1, h, w, 3).astype(int)


def _stream(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)["streams"][0]


def test_output_size_and_frame_count(photo, tmp_path):
    out = str(tmp_path / "kb.mp4")
    res = ken_burns.create_ken_burns(photo, duration=1.0, width=160, height=90, fps=10, output_path=out)
    assert res["output_path"] == out and res["pan"] == "center"
    stream = _stream(out)
    assert (stream["width"], stream["height"]) == (160, 90)
    assert len(_frames(out, 160, 90)) == 10


def test_zoom_changes_picture(photo, tmp_path):
    out = str(tmp_path / "zoom.mp4")
    ken_burns.create_ken_burns(
        photo, duration=1.0, zoom_start=1.0, zoom_end=2.0, width=160, height=90, fps=10, output_path=out
    )
    frames = _frames(out, 160, 90)
    # Zooming into a gradient flattens it: the red channel spans less range at the end.
    span = lambda f: np.ptp(f[45, :, 0])  # noqa: E731
    assert span(frames[-1]) < span(frames[0]) * 0.75


@pytest.mark.parametrize("pan, direction", [("left_to_right", 1), ("right_to_left", -1)])
def test_horizontal_pan_direction(photo, tmp_path, pan, direction):
    out = str(tmp_path / f"{pan}.mp4")
    ken_burns.create_ken_burns(
        photo, duration=1.0, zoom_start=1.5, zoom_end=1.5, pan=pan, width=160, height=90, fps=10, output_path=out
    )
    frames = _frames(out, 160, 90)
    # Red grows left to right in the source, so panning right raises the mean red value.
    delta = frames[-1][..., 0].mean() - frames[0][..., 0].mean()
    assert delta * direction > 10


def test_bad_pan_raises(photo):
    with pytest.raises(ValueError):
        ken_burns.create_ken_burns(photo, pan="spiral")


def test_missing_image_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ken_burns.create_ken_burns(str(tmp_path / "nope.png"))
