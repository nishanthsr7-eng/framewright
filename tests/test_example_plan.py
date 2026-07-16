"""Consistency checks for examples/edit_plan.example.json."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "resolve" / "templates"


@pytest.fixture(scope="module")
def plan():
    return json.loads((ROOT / "examples" / "edit_plan.example.json").read_text(encoding="utf-8"))


def test_top_level_keys(plan):
    assert {"version", "project", "music", "beat_grid", "clips"} <= set(plan)
    assert plan["project"]["fps"] > 0


def test_beat_grid_is_sorted_and_downbeats_are_beats(plan):
    grid = plan["beat_grid"]
    assert grid["beats"] == sorted(grid["beats"])
    assert set(grid["downbeats"]) <= set(grid["beats"])
    sections = grid["sections"]
    assert all(a["end"] == b["start"] for a, b in zip(sections, sections[1:], strict=False))


def test_clips_land_on_beats_without_overlap(plan):
    beats = set(plan["beat_grid"]["beats"])
    by_track = {}
    for clip in plan["clips"]:
        assert clip["out"] > clip["in"] and clip["speed"] > 0
        assert clip["at"] in beats
        by_track.setdefault(clip["track"], []).append(clip)
    for clips in by_track.values():
        clips.sort(key=lambda c: c["at"])
        for a, b in zip(clips, clips[1:], strict=False):
            assert a["at"] + (a["out"] - a["in"]) / a["speed"] <= b["at"] + 1e-6


def test_named_templates_exist(plan):
    wanted = {("Transitions", c["transition_in"]["type"]) for c in plan["clips"] if "transition_in" in c}
    wanted |= {("Effects", e) for c in plan["clips"] for e in c.get("effects", [])}
    wanted |= {("Titles", t["template"]) for t in plan.get("titles", [])}
    missing = [f"{kind}/{name}" for kind, name in wanted if not (TEMPLATES / kind / f"{name}.setting").is_file()]
    assert not missing


def test_markers_inside_timeline(plan):
    end = max(c["at"] + (c["out"] - c["in"]) / c["speed"] for c in plan["clips"])
    assert all(0 <= m["at"] <= end for m in plan.get("markers", []))
