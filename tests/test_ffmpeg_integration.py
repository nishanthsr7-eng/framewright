import json
import os

import pytest
from effects_mcp.effects import apply_effect, apply_transition
from framewright_core import probe_video
from timeline_project_mcp.plan_render import render_plan

pytestmark = pytest.mark.ffmpeg


def test_probe_video_with_audio(media):
    info = probe_video(media["av"])
    assert (info.width, info.height, info.fps, info.has_audio, info.has_video) == (320, 240, 25.0, True, True)
    assert info.duration == pytest.approx(2.0, abs=0.05)


def test_probe_video_without_audio(media):
    assert probe_video(media["v"]).has_audio is False


def test_probe_video_rejects_missing_file(media):
    with pytest.raises(RuntimeError, match="ffprobe failed"):
        probe_video(os.path.join(media["dir"], "missing.mp4"))


def test_apply_effect_keeps_size_and_duration(media, tmp_path):
    out = str(tmp_path / "shake.mp4")
    r = apply_effect(media["av"], "shake", intensity=1.0, start_time=0.5, duration=1.0, output_path=out)
    info = probe_video(r["output_path"])
    assert (info.width, info.height, info.has_audio) == (320, 240, True)
    assert info.duration == pytest.approx(2.0, abs=0.1)


def test_apply_effect_lossless(media, tmp_path):
    r = apply_effect(media["v"], "grade_warm", output_path=str(tmp_path / "w.mp4"), lossless=True)
    assert probe_video(r["output_path"]).duration == pytest.approx(1.0, abs=0.1)


def test_apply_transition_overlaps_the_clips(media, tmp_path):
    r = apply_transition(media["av"], media["av"], "fade", duration=0.5, output_path=str(tmp_path / "t.mp4"))
    assert probe_video(r["output_path"]).duration == pytest.approx(3.5, abs=0.15)


def test_render_plan_is_frame_exact(media, tmp_path):
    plan = {
        "version": "0.1",
        "project": {"name": "t", "width": 320, "height": 240, "fps": 25},
        "clips": [
            {"file": media["av"], "in": 0.0, "out": 0.6, "at": 0.0, "track": 1},
            {"file": media["v"], "in": 0.0, "out": 0.6, "at": 0.6, "track": 1, "transition_in": {"type": "flash"}},
        ],
        "titles": [],
    }
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    r = render_plan(str(p), output_path=str(tmp_path / "out.mp4"))
    info = probe_video(r["output_path"])
    assert (info.width, info.height) == (320, 240)
    assert r["cuts"] == 2 and r["flashes"] == 1
    assert info.duration == pytest.approx(1.2, abs=1 / 25 + 0.01)
