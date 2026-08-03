import json
import subprocess

import pytest

plan_render = pytest.importorskip("timeline_project_mcp.plan_render")


def _write_plan(tmp_path, media, **extra):
    plan = {
        "version": "0.1",
        "project": {"name": "t", "width": 320, "height": 180, "fps": 25},
        "music": {"file": media["a"], "start": 0.0, "gain_db": 0},
        "clips": [
            {"file": media["a"], "in": 0.0, "out": 1.0, "track": 1, "at": 0.0, "speed": 1.0},
            {
                "file": media["b"],
                "in": 0.5,
                "out": 1.0,
                "track": 1,
                "at": 1.0,
                "speed": 0.5,
                "transition_in": {"type": "Flash White", "frames": 3},
                "effects": ["Screen Shake"],
            },
            {"file": media["b"], "in": 0.0, "out": 1.0, "track": 2, "at": 0.0, "speed": 1.0},
        ],
        "titles": [{"text": "HELLO", "at": 0.2, "duration": 0.5, "track": 2, "template": "Center Title"}],
        "markers": [],
    }
    plan.update(extra)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan), encoding="utf-8")
    return str(path)


def test_render_plan(media, tmp_path):
    out = str(tmp_path / "render.mp4")
    res = plan_render.render_plan(_write_plan(tmp_path, media), output_path=out, base_dir=str(tmp_path))
    assert res["expected_duration"] == pytest.approx(2.0)
    assert res["duration"] == pytest.approx(2.0, abs=0.1)
    assert (res["width"], res["height"]) == (320, 180)
    assert res["cuts"] == 2 and res["skipped_other_tracks"] == 1
    assert res["flashes"] == 1 and res["shakes"] == 1 and res["titles"] == 1
    probe = json.loads(
        subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", out],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )
    assert {s["codec_type"] for s in probe["streams"]} == {"video", "audio"}


def test_render_plan_tiktok(media, tmp_path):
    out = str(tmp_path / "tiktok.mp4")
    res = plan_render.render_plan(
        _write_plan(tmp_path, media, titles=[]), output_path=out, platform="tiktok", base_dir=str(tmp_path)
    )
    assert (res["width"], res["height"]) == plan_render.PLATFORMS["tiktok"]


def test_render_plan_rejects_bad_plans(media, tmp_path):
    with pytest.raises(ValueError):
        plan_render.render_plan(_write_plan(tmp_path, media, project={"name": "t"}), base_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        bad = [{"file": "missing.mp4", "in": 0, "out": 1, "track": 1, "at": 0}]
        plan_render.render_plan(_write_plan(tmp_path, media, clips=bad), base_dir=str(tmp_path))
