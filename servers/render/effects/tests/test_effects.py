import json
import subprocess

import pytest

effects = pytest.importorskip("effects_mcp.effects")


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def _duration(path):
    return float(_probe(path)["format"]["duration"])


@pytest.mark.parametrize("effect", sorted(effects.EFFECTS))
def test_every_effect_renders(media, tmp_path, effect):
    out = str(tmp_path / f"{effect}.mp4")
    res = effects.apply_effect(media["av"], effect, start_time=0.2, duration=0.5, output_path=out)
    assert res["output_path"] == out and res["effect"] == effect
    if effect != "speed_ramp":
        assert _duration(out) == pytest.approx(1.0, abs=0.1)


def test_effect_on_clip_without_audio(media, tmp_path):
    out = str(tmp_path / "flash.mp4")
    effects.apply_effect(media["v"], "flash", output_path=out)
    assert [s["codec_type"] for s in _probe(out)["streams"]] == ["video"]


def test_unknown_effect_raises(media):
    with pytest.raises(ValueError):
        effects.apply_effect(media["av"], "explode")


@pytest.mark.parametrize("transition", ["fade", "wipeleft", "circleopen"])
def test_transition_overlaps_clips(media, tmp_path, transition):
    out = str(tmp_path / f"{transition}.mp4")
    res = effects.apply_transition(media["av"], media["av"], transition=transition, duration=0.4, output_path=out)
    assert res["transition"] == transition
    assert _duration(out) == pytest.approx(1.6, abs=0.15)


def test_unknown_transition_raises(media):
    with pytest.raises(ValueError):
        effects.apply_transition(media["av"], media["av"], transition="spin")


def test_listings():
    assert "fade" in effects.list_transitions()
    assert set(effects.list_effects()) == set(effects.EFFECTS)
