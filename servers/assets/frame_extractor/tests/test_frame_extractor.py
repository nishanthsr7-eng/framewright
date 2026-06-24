import json
import os
import subprocess

import pytest

cut_video = pytest.importorskip("ffmpeg_mcp.cut_video")
utils = pytest.importorskip("ffmpeg_mcp.utils")


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "value, seconds",
    [(90, 90.0), (1.5, 1.5), ("45", 45.0), ("01:30", 90.0), ("01:02:03", 3723.0), ((1, 30), 90.0), ((1, 0, 0), 3600.0)],
)
def test_convert_to_seconds(value, seconds):
    assert utils.convert_to_seconds(value) == seconds


@pytest.mark.parametrize("value", ["1:2:3:4", (1, 2, 3, 4), [1, 2]])
def test_convert_to_seconds_rejects_bad_input(value):
    with pytest.raises(ValueError):
        utils.convert_to_seconds(value)


def test_clip_video(clip, tmp_path):
    out = str(tmp_path / "cut.mp4")
    res = cut_video.clip_video_ffmpeg(clip, start=0.5, duration=1, output_path=out)
    assert res["code"] == 0 and res["output_path"] == out
    assert float(_probe(out)["format"]["duration"]) == pytest.approx(1.0, abs=0.1)


def test_scale_video(clip, tmp_path):
    out = str(tmp_path / "small.mp4")
    res = cut_video.scale_video(clip, 160, output_path=out)
    assert res["code"] == 0
    stream = _probe(out)["streams"][0]
    assert (stream["width"], stream["height"]) == (160, 120)


@pytest.mark.parametrize("fast", [True, False])
def test_concat_videos(clip, tmp_path, fast):
    out = str(tmp_path / "joined.mp4")
    code, _log = cut_video.concat_videos([clip, clip], output_path=out, fast=fast)
    assert code == 0
    assert float(_probe(out)["format"]["duration"]) == pytest.approx(4.0, abs=0.2)


def test_concat_missing_input_raises(clip, tmp_path):
    with pytest.raises(FileNotFoundError):
        cut_video.concat_videos([clip, str(tmp_path / "nope.mp4")])


def test_extract_every_frame(clip, tmp_path):
    res = cut_video.extract_frames_from_video(clip, output_folder=str(tmp_path))
    assert res["code"] == 0
    assert len([f for f in os.listdir(tmp_path) if f.endswith(".png")]) == 50


def test_extract_limited_jpg_frames(clip, tmp_path):
    res = cut_video.extract_frames_from_video(clip, output_folder=str(tmp_path), format=1, total_frames=5)
    assert res["code"] == 0
    assert sorted(os.listdir(tmp_path)) == [f"frame_{i:04d}.jpg" for i in range(1, 6)]
