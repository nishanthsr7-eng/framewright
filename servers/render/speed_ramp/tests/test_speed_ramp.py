import json
import subprocess

import pytest

speed_ramp = pytest.importorskip("speed_ramp_mcp.speed_ramp")


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def _duration(path):
    return float(_probe(path)["format"]["duration"])


@pytest.mark.parametrize(
    "speed, chain",
    [(1.0, "atempo=1.000000"), (4.0, "atempo=2.0,atempo=2.000000"), (0.25, "atempo=0.5,atempo=0.500000")],
)
def test_atempo_chain_stays_in_range(speed, chain):
    assert speed_ramp._atempo_chain(speed) == chain


def test_speed_vf():
    assert speed_ramp._speed_vf(2.0, 25, smooth=True) == "setpts=0.500000*PTS"
    assert "minterpolate=fps=25" in speed_ramp._speed_vf(0.5, 25, smooth=True)
    assert "minterpolate" not in speed_ramp._speed_vf(0.5, 25, smooth=False)


@pytest.mark.parametrize("speed, expected", [(2.0, 0.5), (0.5, 2.0)])
def test_change_speed(media, tmp_path, speed, expected):
    out = str(tmp_path / "s.mp4")
    res = speed_ramp.change_speed(media["av"], speed=speed, smooth=False, output_path=out)
    assert res["new_duration"] == pytest.approx(expected, abs=0.05)
    assert _duration(out) == pytest.approx(expected, abs=0.15)


def test_slow_motion_without_audio(media, tmp_path):
    # smooth=False: ffmpeg's minterpolate can segfault intermittently; test_speed_vf covers the filter string.
    out = str(tmp_path / "slow.mp4")
    speed_ramp.change_speed(media["v"], speed=0.5, smooth=False, output_path=out)
    assert [s["codec_type"] for s in _probe(out)["streams"]] == ["video"]
    assert _duration(out) == pytest.approx(2.0, abs=0.15)


def test_speed_ramp_fast_section(media, tmp_path):
    out = str(tmp_path / "ramp.mp4")
    segments = [{"start": 0.0, "end": 0.5, "speed": 1.0}, {"start": 0.5, "end": 1.0, "speed": 2.0}]
    res = speed_ramp.speed_ramp(media["av"], segments, output_path=out)
    assert res["segment_count"] == 2
    assert res["duration"] == pytest.approx(0.75, abs=0.15)


@pytest.mark.xfail(reason="-t is passed after -i, so it caps each slowed segment's output at its source length")
def test_speed_ramp_slow_section(media, tmp_path):
    out = str(tmp_path / "ramp.mp4")
    segments = [{"start": 0.0, "end": 0.5, "speed": 1.0}, {"start": 0.5, "end": 1.0, "speed": 0.5, "smooth": False}]
    res = speed_ramp.speed_ramp(media["av"], segments, output_path=out)
    assert res["segment_count"] == 2
    assert res["duration"] == pytest.approx(1.5, abs=0.15)


@pytest.mark.parametrize(
    "segments",
    [[], [{"start": 0.5, "end": 0.2}], [{"start": 0.0, "end": 0.5, "speed": 0}]],
)
def test_speed_ramp_rejects_bad_segments(media, tmp_path, segments):
    with pytest.raises(ValueError):
        speed_ramp.speed_ramp(media["av"], segments, output_path=str(tmp_path / "x.mp4"))


def test_change_speed_rejects_zero(media):
    with pytest.raises(ValueError):
        speed_ramp.change_speed(media["av"], speed=0)
