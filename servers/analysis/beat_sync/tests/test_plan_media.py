"""build_edit_plan / auto_amv_plan / validate_plan on real (tiny) media."""

import json
import os
import subprocess

import pytest

plan_mod = pytest.importorskip("beat_sync_mcp.plan")
amv = pytest.importorskip("beat_sync_mcp.amv")


@pytest.fixture
def out_root(tmp_path, monkeypatch):
    """Keep framewright_plan.lua out of the repo's output/ folder."""
    root = tmp_path / "output"
    monkeypatch.setattr(plan_mod, "_get_output_root", lambda: str(root))
    monkeypatch.setattr(amv, "_get_output_root", lambda: str(root))
    return root


@pytest.fixture(scope="module")
def cut_clips(media, tmp_path_factory):
    """3 s clips with a hard cut at 1.5 s, so the scene filter finds shots."""
    d = tmp_path_factory.mktemp("amv")
    out = []
    for n, (a, b) in enumerate((("testsrc", "smptebars"), ("rgbtestsrc", "testsrc2"))):
        path = d / f"cut{n}.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"{a}=size=160x120:rate=25:duration=1.5",
                "-f",
                "lavfi",
                "-i",
                f"{b}=size=160x120:rate=25:duration=1.5",
                "-filter_complex",
                "[0:v][1:v]concat=n=2:v=1:a=0",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        out.append(str(path))
    return out


def test_build_edit_plan_round_trip(media, out_root, tmp_path):
    path = str(tmp_path / "plan.json")
    res = plan_mod.build_edit_plan(media["clips"], media["music"], output_path=path, beats_per_cut=2, max_duration=4)
    assert res["output_path"] == path and res["duration"] == pytest.approx(4.0)
    assert res["fps"] == 25.0 and res["bpm"] == pytest.approx(120, rel=0.05)

    with open(path, encoding="utf-8") as f:
        plan = json.load(f)
    clips = plan["clips"]
    assert len(clips) == res["clip_count"] >= 2
    assert clips[0]["at"] == 0.0
    assert {c["file"] for c in clips} == set(media["clips"])
    for a, b in zip(clips, clips[1:], strict=False):
        assert a["at"] + (a["out"] - a["in"]) == pytest.approx(b["at"], abs=0.002)

    report = plan_mod.validate_plan(path, base_dir=str(tmp_path))
    assert report["valid"], report["errors"]
    assert report["timeline_duration"] == pytest.approx(4.0, abs=0.01)

    lua = (out_root / "framewright_plan.lua").read_text(encoding="utf-8")
    assert lua.startswith("return {") and "beat_grid" not in lua


def test_validate_catches_broken_plan(media, out_root, tmp_path):
    path = str(tmp_path / "plan.json")
    plan_mod.build_edit_plan(media["clips"], media["music"], output_path=path, max_duration=3)
    with open(path, encoding="utf-8") as f:
        plan = json.load(f)
    plan["clips"][0]["out"] = 99.0  # past the end of a 3 s clip, and overlaps the next cut
    plan["clips"].append(dict(plan["clips"][-1], file=os.path.join(str(tmp_path), "gone.mp4")))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f)
    report = plan_mod.validate_plan(path, base_dir=str(tmp_path))
    assert not report["valid"]
    text = " ".join(report["errors"])
    assert "past the clip end" in text and "file not found" in text and "overlap" in text


def test_auto_amv_plan_is_valid(media, cut_clips, out_root, tmp_path):
    path = str(tmp_path / "amv.json")
    res = amv.auto_amv_plan(cut_clips, media["music"], output_path=path, end_time=4, style="general", title="TEST")
    assert res["output_path"] == path and res["clip_count"] >= 1 and res["shots_available"] >= 1
    assert os.path.isfile(res["resolve_lua"])
    with open(path, encoding="utf-8") as f:
        plan = json.load(f)
    assert plan["titles"][0]["text"] == "TEST"
    assert all(0.25 <= c["speed"] <= 1.0 for c in plan["clips"])
    report = plan_mod.validate_plan(path, base_dir=str(tmp_path), require_beats=False)
    assert report["valid"], report["errors"]


@pytest.mark.xfail(reason="the scene-select output gets no frames on a clip without cuts, and ffmpeg 8 errors")
def test_auto_amv_plan_single_shot_clips(media, out_root, tmp_path):
    res = amv.auto_amv_plan(media["clips"], media["music"], output_path=str(tmp_path / "a.json"), end_time=4)
    assert res["clip_count"] >= 1


def test_auto_amv_rejects_audio_as_clip(media, out_root):
    with pytest.raises(ValueError):
        amv.auto_amv_plan([media["music"]], media["music"])
