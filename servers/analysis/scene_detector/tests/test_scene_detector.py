import os

import pytest

detector = pytest.importorskip("scene_detector_mcp.detector")


def test_detect_scenes_finds_cuts(three_shots):
    res = detector.detect_scenes(three_shots, min_scene_len=5)
    assert res["scene_count"] == 3
    starts = [s["start"] for s in res["scenes"]]
    assert starts == pytest.approx([0.0, 1.0, 2.0], abs=0.05)
    assert [s["index"] for s in res["scenes"]] == [1, 2, 3]


def test_high_threshold_finds_fewer_cuts(three_shots):
    loose = detector.detect_scenes(three_shots, min_scene_len=5)
    strict = detector.detect_scenes(three_shots, threshold=255.0, min_scene_len=5)
    assert strict["scene_count"] < loose["scene_count"]


def test_split_scenes_writes_files(three_shots, tmp_path):
    res = detector.split_scenes(three_shots, output_folder=str(tmp_path), min_scene_len=5)
    assert res["scene_count"] == 3
    assert all(os.path.getsize(s["file"]) > 0 for s in res["scenes"])


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        detector.detect_scenes(str(tmp_path / "nope.mp4"))
