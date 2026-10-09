import json
import re
import subprocess

import pytest

mastering = pytest.importorskip("audio_mastering_mcp.mastering")


def _loudness(path):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", out.stderr)[-1])


def _rms_db(path):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    m = re.search(r"mean_volume:\s+(-?[\d.]+) dB", out.stderr)
    assert m, out.stderr
    return float(m.group(1))


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def test_normalize_loudness_hits_target(media, tmp_path):
    out = str(tmp_path / "loud.wav")
    res = mastering.normalize_loudness(media["quiet"], target_lufs=-16.0, output_path=out)
    assert res == {"output_path": out, "target_lufs": -16.0}
    assert _loudness(media["quiet"]) < -25
    assert _loudness(out) == pytest.approx(-16.0, abs=2.0)


def test_normalize_keeps_video(media, tmp_path):
    out = str(tmp_path / "norm.mp4")
    mastering.normalize_loudness(media["av"], output_path=out)
    assert {s["codec_type"] for s in _probe(out)["streams"]} == {"video", "audio"}


def test_reduce_noise_lowers_level(media, tmp_path):
    out = str(tmp_path / "clean.wav")
    assert mastering.reduce_noise(media["noisy"], amount=30, output_path=out)["amount"] == 30
    assert _rms_db(out) < _rms_db(media["noisy"]) - 3


def test_no_audio_raises(media):
    with pytest.raises(RuntimeError):
        mastering.normalize_loudness(media["v"])
    with pytest.raises(RuntimeError):
        mastering.reduce_noise(media["v"])


@pytest.mark.parametrize("src, duck", [("av", True), ("av", False), ("v", True)])
def test_add_background_music(media, tmp_path, src, duck):
    out = str(tmp_path / "bgm.mp4")
    res = mastering.add_background_music(media[src], media["music"], duck=duck, output_path=out)
    assert res["duck"] == duck
    info = _probe(out)
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    # The 1 s music bed loops to cover the 2 s video.
    assert float(info["format"]["duration"]) == pytest.approx(2.0, abs=0.15)


def test_background_music_needs_video(media):
    with pytest.raises(RuntimeError):
        mastering.add_background_music(media["quiet"], media["music"])
