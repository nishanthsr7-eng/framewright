import pytest

analyzer = pytest.importorskip("audio_analyzer_mcp.analyzer")


def test_audio_info(click_track):
    info = analyzer.get_audio_info(click_track)
    assert info["duration"] == pytest.approx(8.0, abs=0.01)
    assert info["sample_rate"] == 22050
    assert 0 < info["rms_mean"] <= info["rms_max"]


def test_detect_beats_tempo(click_track):
    res = analyzer.detect_beats(click_track)
    assert res["tempo_bpm"] == pytest.approx(120, rel=0.05)
    assert res["beat_count"] == len(res["beat_times"]) >= 8
    assert res["beat_times"] == sorted(res["beat_times"])


def test_detect_beats_start_offset(click_track):
    res = analyzer.detect_beats(click_track, start_time=2.0, duration=4.0)
    assert all(2.0 <= t <= 6.0 for t in res["beat_times"])


def test_detect_downbeats_sparser_than_beats(click_track):
    beats = analyzer.detect_beats(click_track)
    down = analyzer.detect_downbeats(click_track, beats_per_bar=4)
    assert down["beats_per_bar"] == 4
    assert 0 < down["downbeat_count"] < beats["beat_count"]


def test_detect_impacts(click_track):
    res = analyzer.detect_impacts(click_track)
    assert res["impact_count"] == len(res["impacts"]) > 0
    assert all({"time", "strength"} <= set(i) for i in res["impacts"])


def test_detect_sections_cover_track(click_track):
    sections = analyzer.detect_sections(click_track, n_sections=3)["sections"]
    assert sections
    assert sections[0]["label"] == "intro"
    assert all(s["start"] < s["end"] for s in sections)


def test_audio_features_windows(click_track):
    res = analyzer.analyze_audio_features(click_track, window=2.0)
    assert res["window_seconds"] == 2.0
    times = [w["time"] for w in res["windows"]]
    assert times[0] == 0.0 and len(times) >= 4
    assert all(b - a == pytest.approx(2.0, abs=0.05) for a, b in zip(times, times[1:], strict=False))
    assert res["summary"]["rms_max"] >= res["summary"]["rms_mean"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        analyzer.get_audio_info(str(tmp_path / "nope.wav"))
