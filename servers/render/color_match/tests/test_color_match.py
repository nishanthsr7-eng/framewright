import pytest

color_match = pytest.importorskip("color_match_mcp.color_match")


def test_color_profile(media):
    plain = color_match.get_color_profile(media["plain"], samples=2)
    moody = color_match.get_color_profile(media["moody"], samples=2)
    assert plain["samples"] == 2 and len(plain["mean_rgb"]) == 3
    assert moody["mean_rgb"][0] < plain["mean_rgb"][0]
    assert moody["mean_rgb"][2] > moody["mean_rgb"][0]


def test_match_color_moves_target_toward_reference(media, tmp_path):
    out = str(tmp_path / "matched.mp4")
    res = color_match.match_color(media["moody"], media["plain"], output_path=out, samples=2)
    assert res["output_path"] == out
    assert all(0.5 <= g <= 2.0 for g in res["gains_rgb"])
    ref = color_match.get_color_profile(media["moody"], samples=2)["mean_rgb"]
    before = color_match.get_color_profile(media["plain"], samples=2)["mean_rgb"]
    after = color_match.get_color_profile(out, samples=2)["mean_rgb"]
    for c in range(3):
        assert abs(after[c] - ref[c]) < abs(before[c] - ref[c]) or abs(after[c] - ref[c]) < 5


def test_zero_strength_is_identity(media, tmp_path):
    res = color_match.match_color(
        media["moody"], media["plain"], output_path=str(tmp_path / "x.mp4"), samples=2, strength=0.0
    )
    assert res["gains_rgb"] == [1.0, 1.0, 1.0]
    assert res["offsets_rgb"] == pytest.approx([0.0, 0.0, 0.0])


def test_missing_file_raises(media, tmp_path):
    with pytest.raises(FileNotFoundError):
        color_match.match_color(media["plain"], str(tmp_path / "nope.mp4"))
