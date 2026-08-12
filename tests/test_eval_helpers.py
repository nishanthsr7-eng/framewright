"""The eval fixtures and metrics must be right, or the eval numbers mean nothing."""

import importlib.util
import json
import shutil
import subprocess
import wave
from pathlib import Path

import pytest

EVALS = Path(__file__).resolve().parent.parent / "evals"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, EVALS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def fixtures():
    return _load("make_fixtures")


def test_click_track_beats_and_length(fixtures, tmp_path):
    path = tmp_path / "click.wav"
    beats = fixtures.click_track(path, bpm=120, seconds=4)
    assert beats == [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    with wave.open(str(path)) as w:
        assert w.getframerate() == fixtures.SR and w.getnframes() == 4 * fixtures.SR


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
def test_cut_video_reports_cut_times(fixtures, tmp_path):
    path = tmp_path / "cuts.mp4"
    cuts = fixtures.cut_video(path, [("color=c=red", 0.8), ("testsrc", 1.2), ("color=c=blue", 0.6)])
    assert cuts == [0.8, 2.0]
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert float(json.loads(out.stdout)["format"]["duration"]) == pytest.approx(2.6, abs=0.05)


@pytest.fixture(scope="module")
def scenes():
    pytest.importorskip("scene_detector_mcp")
    return _load("eval_scenes")


@pytest.mark.parametrize(
    "detected, truth, expected",
    [
        ([1.0, 2.0], [1.0, 2.0], (1.0, 1.0, 1.0)),
        ([1.02], [1.0, 2.0], (1.0, 0.5, 2 / 3)),
        ([1.0, 1.01], [1.0], (0.5, 1.0, 2 / 3)),  # one truth cut can only be matched once
        ([5.0], [1.0], (0.0, 0.0, 0.0)),
        ([], [1.0], (0.0, 0.0, 0.0)),
    ],
)
def test_prf(scenes, detected, truth, expected):
    assert scenes.prf(detected, truth, tol=0.05) == pytest.approx(expected)
