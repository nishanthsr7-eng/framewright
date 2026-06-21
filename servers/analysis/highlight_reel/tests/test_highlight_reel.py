import os

import pytest

highlights = pytest.importorskip("highlight_reel_mcp.highlights")


def test_picks_the_loud_part(media, tmp_path):
    out = str(tmp_path / "reel.mp4")
    res = highlights.generate_highlights(media["burst"], target_duration=3.0, clip_duration=3.0, output_path=out)
    assert os.path.getsize(out) > 0
    assert len(res["segments"]) == 1
    seg = res["segments"][0]
    assert seg["start"] < 8.0 and seg["end"] > 6.0
    assert res["total_duration"] == pytest.approx(3.0)


def test_segments_respect_min_gap(media, tmp_path):
    res = highlights.generate_highlights(
        media["burst"], target_duration=6.0, clip_duration=2.0, min_gap=3.0, output_path=str(tmp_path / "r.mp4")
    )
    centers = [(s["start"] + s["end"]) / 2 for s in res["segments"]]
    assert centers == sorted(centers)
    assert all(b - a >= 3.0 for a, b in zip(centers, centers[1:], strict=False))


def test_video_without_audio_raises(media):
    with pytest.raises(RuntimeError):
        highlights.generate_highlights(media["no_audio"], clip_duration=1.0)


def test_too_short_raises(media):
    with pytest.raises(ValueError):
        highlights.generate_highlights(media["burst"], clip_duration=20.0)
