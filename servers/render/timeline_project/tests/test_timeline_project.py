import json
import subprocess

import pytest

tp = pytest.importorskip("timeline_project_mcp.project")


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def test_create_and_edit_project(media, project):
    created = tp.create_project(project, width=320, height=180, fps=25)
    assert created == {"width": 320, "height": 180, "fps": 25.0, "clips": [], "overlays": []}

    first = tp.add_clip(project, media["a"], start=0.5)
    assert first["index"] == 0 and first["clip"]["end"] == pytest.approx(2.0, abs=0.05)
    second = tp.add_clip(project, media["b"], end=1.5, transition_in="fade", transition_in_duration=0.5)
    assert second["clip_count"] == 2 and second["clip"]["transition_in"] == "fade"

    ov = tp.add_overlay(project, media["logo"], x=5, y=5, end_time=1.0)
    assert ov["overlay"]["end_time"] == 1.0 and "width" not in ov["overlay"]

    state = tp.get_project(project)
    assert state["estimated_duration"] == pytest.approx(1.5 + 1.5 - 0.5, abs=0.05)
    with open(project, encoding="utf-8") as f:
        assert len(json.load(f)["clips"]) == 2


def test_remove_items(media, project):
    tp.create_project(project)
    tp.add_clip(project, media["a"])
    tp.add_overlay(project, media["logo"])
    assert tp.remove_clip(project, 0)["clip_count"] == 0
    assert tp.remove_overlay(project, 0)["overlay_count"] == 0
    with pytest.raises(IndexError):
        tp.remove_clip(project, 0)
    with pytest.raises(IndexError):
        tp.remove_overlay(project, -1)


def test_missing_files_raise(media, project, tmp_path):
    with pytest.raises(FileNotFoundError):
        tp.get_project(str(tmp_path / "none.json"))
    tp.create_project(project)
    with pytest.raises(FileNotFoundError):
        tp.add_clip(project, str(tmp_path / "nope.mp4"))


def test_render_empty_project_raises(project):
    tp.create_project(project)
    with pytest.raises(ValueError):
        tp.render_project(project)


def test_render_project(media, project, tmp_path):
    tp.create_project(project, width=320, height=180, fps=25)
    tp.add_clip(project, media["a"], start=0.0, end=1.5)
    tp.add_clip(project, media["b"], start=0.0, end=1.5, transition_in="fade", transition_in_duration=0.5)
    tp.add_clip(project, media["still"], start=0.0, end=1.0)
    tp.add_overlay(project, media["logo"], x=10, y=10, start_time=0.0, end_time=1.0)
    out = str(tmp_path / "render.mp4")
    res = tp.render_project(project, output_path=out)
    assert res["clip_count"] == 3 and res["overlay_count"] == 1
    expected = tp.get_project(project)["estimated_duration"]
    assert res["duration"] == pytest.approx(expected, abs=0.25)
    video = next(s for s in _probe(out)["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (320, 180)
