import pytest
from effects_mcp.effects import EFFECTS, _build_filter
from framewright_core import VideoInfo

INFO = VideoInfo(width=1280, height=720, duration=4.0, fps=25.0, has_audio=True)


def test_shake_crops_by_twice_the_amplitude_and_scales_back():
    f = _build_filter("shake", INFO, 1.0, 1.0, 2.0)
    assert f.startswith("crop=w='1280-12':h='720-12'")
    assert "between(t,1.0,2.0)" in f and f.endswith("scale=1280:720")


def test_rgb_split_pixel_shift_follows_intensity():
    assert (
        _build_filter("rgb_split", INFO, 2.0, 0.0, 1.0) == "rgbashift=rh=6:bh=-6:edge=smear:enable='between(t,0.0,1.0)'"
    )


def test_flash_brightness_is_capped_at_one_and_ends_early():
    f = _build_filter("flash", INFO, 3.0, 1.0, 5.0)
    assert ",1.0,0)" in f  # brightness capped
    assert "between(t,1.0,1.45)" in f  # 0.15 * intensity


def test_zoom_punch_centres_on_the_window():
    f = _build_filter("zoom_punch", INFO, 1.0, 2.0, 4.0)
    assert "(t-3.0)" in f and "crop=w=1280:h=720" in f


def test_speed_ramp_factor_is_clamped():
    assert _build_filter("speed_ramp", INFO, 10.0, 0, 1) == ("__speed__", 4.0)
    assert _build_filter("speed_ramp", INFO, 0.1, 0, 1) == ("__speed__", 0.25)


def test_glow_is_a_split_blend_graph():
    f = _build_filter("glow", INFO, 1.0, 0.0, 1.0)
    assert f.startswith("split[gb_a][gb_b];") and "blend=all_mode=screen" in f


@pytest.mark.parametrize("effect", sorted(EFFECTS))
def test_every_listed_effect_builds(effect):
    assert _build_filter(effect, INFO, 1.0, 0.0, 1.0)


def test_unknown_effect_raises():
    with pytest.raises(ValueError, match="Unknown effect"):
        _build_filter("sepia", INFO, 1.0, 0.0, 1.0)
