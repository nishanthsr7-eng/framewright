import json
import subprocess

import pytest

np = pytest.importorskip("numpy")
exporter = pytest.importorskip("export_presets_mcp.exporter")


def _video_stream(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    streams = json.loads(out.stdout)["streams"]
    return next(s for s in streams if s["codec_type"] == "video"), streams


def _first_frame_gray(path, w, h):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(h, w)


def test_presets_are_consistent():
    for name, p in exporter.list_platform_presets().items():
        w, h = (int(x) for x in p["aspect"].split(":"))
        assert p["width"] * h == p["height"] * w, name


@pytest.mark.parametrize("platform", ["instagram_post", "tiktok"])
def test_export_matches_preset_size(media, tmp_path, platform):
    out = str(tmp_path / f"{platform}.mp4")
    res = exporter.export_for_platform(media["av"], platform, output_path=out)
    stream, streams = _video_stream(out)
    preset = exporter.PRESETS[platform]
    assert (stream["width"], stream["height"]) == (preset["width"], preset["height"]) == (res["width"], res["height"])
    assert {s["codec_type"] for s in streams} == {"video", "audio"}


def test_pad_mode_letterboxes(media, tmp_path):
    out = str(tmp_path / "pad.mp4")
    exporter.export_for_platform(media["av"], "tiktok", output_path=out, fit_mode="pad")
    frame = _first_frame_gray(out, 1080, 1920)
    assert frame[:200].max() < 30 and frame[-200:].max() < 30  # black bars above and below
    assert frame[900:1000].mean() > 30


def test_fps_is_capped(media, tmp_path):
    out = str(tmp_path / "capped.mp4")
    exporter.export_for_platform(media["v60"], "instagram_post", output_path=out)
    stream, streams = _video_stream(out)
    assert stream["r_frame_rate"] == "30/1"
    assert len(streams) == 1


def test_bad_options_raise(media):
    with pytest.raises(ValueError):
        exporter.export_for_platform(media["av"], "myspace")
    with pytest.raises(ValueError):
        exporter.export_for_platform(media["av"], "youtube", fit_mode="stretch")
