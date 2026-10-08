import json

import pytest
from beat_sync_mcp import plan as plan_mod

FPS = 25.0
MEDIA = {
    "a.mp4": {"duration": 4.0, "fps": FPS, "width": 640, "height": 360},
    "b.mp4": {"duration": 1.0, "fps": FPS, "width": 640, "height": 360},
    "song.wav": {"duration": 10.0, "fps": None, "width": None, "height": None},
}


@pytest.fixture(autouse=True)
def fake_media(monkeypatch, tmp_path):
    """Replace ffprobe with a table keyed by file name; unknown names are missing files."""

    def info(path):
        name = path.replace("\\", "/").rsplit("/", 1)[-1]
        if name not in MEDIA:
            raise FileNotFoundError(path)
        return MEDIA[name]

    monkeypatch.setattr(plan_mod, "_media_info", info)
    monkeypatch.setattr(plan_mod, "_get_output_root", lambda: str(tmp_path / "output"))


def make_plan(tmp_path, clips, beats=(0.0, 1.0, 2.0, 3.0), **extra):
    plan = {
        "version": plan_mod.PLAN_VERSION,
        "project": {"name": "t", "width": 640, "height": 360, "fps": FPS},
        "music": {"file": "song.wav", "start": 0.0},
        "beat_grid": {"beats": list(beats)},
        "clips": clips,
        **extra,
    }
    p = tmp_path / "plan.json"
    p.write_text(json.dumps(plan), encoding="utf-8")
    return plan_mod.validate_plan(str(p), base_dir=str(tmp_path))


def clip(at, i=0.0, o=1.0, file="a.mp4", **kw):
    return {"file": file, "in": i, "out": o, "at": at, "track": 1, **kw}


def test_valid_plan_on_beats(tmp_path):
    r = make_plan(tmp_path, [clip(0.0), clip(1.0, 1.0, 2.0), clip(2.0, 2.0, 3.0)])
    assert r["valid"] and r["errors"] == [] and r["warnings"] == []
    assert r["timeline_duration"] == 3.0 and r["clip_count"] == 3


def test_missing_file_is_an_error(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, file="nope.mp4")])
    assert not r["valid"] and "file not found: nope.mp4" in r["errors"][0]


def test_out_past_clip_end_is_an_error(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, 0.0, 1.5, file="b.mp4")])
    assert any("past the clip end" in e for e in r["errors"])


def test_out_within_one_frame_of_end_is_allowed(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, 0.0, 1.0 + 0.5 / FPS, file="b.mp4")])
    assert r["valid"]


def test_overlapping_clips_on_a_track(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, 0.0, 2.0), clip(1.0, 2.0, 3.0)])
    assert any("overlap on track 1" in e for e in r["errors"])


def test_clips_on_different_tracks_may_overlap(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, 0.0, 2.0), clip(1.0, 2.0, 3.0, track=2)])
    assert r["valid"]


def test_off_beat_cut_is_a_warning(tmp_path):
    r = make_plan(tmp_path, [clip(0.0), clip(1.0, 1.0, 1.2), clip(1.2, 1.2, 2.0)])
    assert r["valid"] and any("clips[2]: starts +0.2s off" in w for w in r["warnings"])


def test_cut_within_tolerance_is_on_beat(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, 0.0, 1.02), clip(1.02, 1.02, 2.0)])
    assert not any("off the nearest beat" in w for w in r["warnings"])


def test_require_beats_false_skips_beat_checks(tmp_path):
    plan_kw = make_plan(tmp_path, [clip(0.5)], beats=())
    assert any("beat_grid.beats is empty" in w for w in plan_kw["warnings"])
    p = tmp_path / "plan.json"
    r = plan_mod.validate_plan(str(p), base_dir=str(tmp_path), require_beats=False)
    assert r["warnings"] == []


def test_gap_between_clips_is_a_warning(tmp_path):
    r = make_plan(tmp_path, [clip(0.0), clip(2.0, 1.0, 2.0)])
    assert any("gap of 1.0s" in w for w in r["warnings"])


def test_audio_only_file_used_as_clip(tmp_path):
    r = make_plan(tmp_path, [clip(0.0, file="song.wav")])
    assert any("has no video stream" in e for e in r["errors"])


def test_bad_project_and_reversed_range(tmp_path):
    p = tmp_path / "plan.json"
    p.write_text(json.dumps({"project": {"fps": 0, "width": 0, "height": 1.5}, "clips": [clip(0.0, 2.0, 1.0)]}))
    r = plan_mod.validate_plan(str(p), base_dir=str(tmp_path))
    errs = " | ".join(r["errors"])
    assert "project.fps" in errs and "project.width" in errs and "project.height" in errs
    assert "must be after in" in errs


def test_titles_and_markers_are_checked(tmp_path):
    r = make_plan(tmp_path, [clip(0.0)], titles=[{"text": "", "at": -1, "duration": 1}], markers=[{"at": "x"}])
    errs = " | ".join(r["errors"])
    assert "titles[0]: text is empty" in errs and "titles[0]: at must be" in errs and "markers[0]" in errs


def test_lua_serialiser():
    assert plan_mod._lua(True) == "true"
    assert plan_mod._lua(None) == "nil"
    s = 'a "b"' + chr(10)
    assert plan_mod._lua(s) == json.dumps(s)
    assert plan_mod._lua({"x": [1, 2.5]}) == '{["x"] = {1, 2.5}}'


def test_build_edit_plan_cuts_on_beats_and_wraps_short_clips(tmp_path, monkeypatch):
    monkeypatch.setattr(
        plan_mod, "detect_beats", lambda p: {"beat_times": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5], "tempo": 120.0}
    )
    out = tmp_path / "plan.json"
    r = plan_mod.build_edit_plan(
        ["a.mp4", "b.mp4"], "song.wav", output_path=str(out), beats_per_cut=2, max_duration=3.0
    )
    plan = json.loads(out.read_text(encoding="utf-8"))
    ats = [c["at"] for c in plan["clips"]]
    assert ats == [0.0, 1.0, 2.0]  # every 2nd beat
    assert [c["file"] for c in plan["clips"]] == ["a.mp4", "b.mp4", "a.mp4"]
    assert plan["clips"][2]["in"] == 1.0  # clip a continues where it left off
    assert r["duration"] == 3.0 and r["fps"] == FPS and plan["project"]["width"] == 640
    assert plan_mod.validate_plan(str(out), base_dir=str(tmp_path))["valid"]


def test_build_edit_plan_needs_beats(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_mod, "detect_beats", lambda p: {"beat_times": [0.0], "tempo": 0})
    with pytest.raises(RuntimeError, match="Not enough beats"):
        plan_mod.build_edit_plan(["a.mp4"], "song.wav", output_path=str(tmp_path / "p.json"))
