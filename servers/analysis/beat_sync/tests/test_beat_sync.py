import json
import subprocess

import pytest

beat_sync = pytest.importorskip("beat_sync_mcp.beat_sync")


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def test_detect_beats(media):
    res = beat_sync.detect_beats(media["music"])
    assert res["tempo"] == pytest.approx(120, rel=0.05)
    assert res["duration"] == pytest.approx(6.0, abs=0.01)
    assert len(res["beat_times"]) >= 8


def test_generate_beat_synced_video(media, tmp_path):
    out = str(tmp_path / "synced.mp4")
    res = beat_sync.generate_beat_synced_video(media["clips"], media["music"], output_path=out, max_duration=3.0)
    assert res["output_path"] == out
    assert res["cut_count"] >= 2
    assert res["total_duration"] == pytest.approx(3.0, abs=0.05)
    info = _probe(out)
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    assert float(info["format"]["duration"]) == pytest.approx(3.0, abs=0.3)


def test_beats_per_cut_reduces_cuts(media, tmp_path):
    every = beat_sync.generate_beat_synced_video(
        media["clips"], media["music"], output_path=str(tmp_path / "a.mp4"), max_duration=3.0
    )
    every_other = beat_sync.generate_beat_synced_video(
        media["clips"], media["music"], output_path=str(tmp_path / "b.mp4"), beats_per_cut=2, max_duration=3.0
    )
    assert every_other["cut_count"] < every["cut_count"]


def test_empty_clip_list_raises(media):
    with pytest.raises(ValueError):
        beat_sync.generate_beat_synced_video([], media["music"])


def test_missing_music_raises(media, tmp_path):
    with pytest.raises(FileNotFoundError):
        beat_sync.generate_beat_synced_video(media["clips"], str(tmp_path / "nope.wav"))
