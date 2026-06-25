import os

import pytest

np = pytest.importorskip("numpy")
overlay = pytest.importorskip("text_overlay_mcp.overlay")
renderer = pytest.importorskip("text_overlay_mcp.renderer")


def _alpha(img):
    return np.asarray(img)[..., 3]


def test_every_listed_font_file_exists():
    fonts = renderer.list_fonts()
    assert "anton" in fonts
    for name in fonts:
        assert renderer._load_font(name, 20) is not None


def test_unknown_font_raises():
    with pytest.raises(ValueError):
        renderer._font_entry("comic-sans")


@pytest.mark.parametrize(
    "value, rgba",
    [
        ("#FF0000", (255, 0, 0, 255)),
        ("00ff0080", (0, 255, 0, 128)),
        ((1, 2, 3), (1, 2, 3, 255)),
        ([1, 2, 3, 4], (1, 2, 3, 4)),
    ],
)
def test_parse_color(value, rgba):
    assert renderer._parse_color(value) == rgba


def test_parse_color_rejects_garbage():
    with pytest.raises(ValueError):
        renderer._parse_color("#12")


def test_word_by_word_alpha_ramps_in_order():
    assert renderer._word_alpha(0, 4, 0.0, "word_by_word") == 0.0
    assert renderer._word_alpha(0, 4, 1.0, "word_by_word") == 1.0
    assert renderer._word_alpha(3, 4, 0.5, "word_by_word") == 0.0
    assert renderer._word_alpha(2, 4, 0.0, "none") == 1.0


def test_render_frame_draws_text():
    frame = renderer.render_frame((320, 180), "HELLO", font_size=40, progress=1.0)
    assert frame.size == (320, 180) and frame.mode == "RGBA"
    assert _alpha(frame).max() == 255


def test_render_frame_position():
    top = _alpha(renderer.render_frame((320, 180), "HI", font_size=30, position="top"))
    bottom = _alpha(renderer.render_frame((320, 180), "HI", font_size=30, position="bottom"))
    assert np.nonzero(top)[0].mean() < 90 < np.nonzero(bottom)[0].mean()


def test_word_by_word_starts_hidden():
    frame = renderer.render_frame((320, 180), "ONE TWO", font_size=30, progress=0.0, animation="word_by_word")
    assert _alpha(frame).max() == 0


def test_karaoke_highlights_spoken_words():
    words = [{"word": "ONE", "start": 0.0, "end": 0.5}, {"word": "TWO", "start": 0.5, "end": 1.0}]
    gold = np.array([255, 215, 0])

    def gold_pixels(t):
        px = np.asarray(renderer.render_karaoke_frame((320, 180), words, t, font_size=40, outline_width=0))
        return int((np.all(px[..., :3] == gold, axis=-1) & (px[..., 3] == 255)).sum())

    assert gold_pixels(0.1) < gold_pixels(0.9)


def test_group_lines():
    segments = [{"words": [{"word": str(i), "start": i, "end": i + 0.5} for i in range(5)]}, {"words": []}]
    lines = overlay._group_lines(segments, max_words_per_line=2)
    assert [len(line["words"]) for line in lines] == [2, 2, 1]
    assert (lines[0]["start"], lines[0]["end"]) == (0, 1.5)


def test_create_text_overlay(clip, tmp_path):
    code, msg, folder = overlay.create_text_overlay(clip, "HELLO", output_folder=str(tmp_path), duration=0.5)
    assert code == 0, msg
    assert folder == str(tmp_path)
    produced = os.listdir(tmp_path)
    assert "overlay.webm" in produced and any(f.endswith(".mp4") for f in produced)


def test_create_karaoke_captions(clip, tmp_path):
    segments = [{"words": [{"word": "HI", "start": 0.0, "end": 0.4}, {"word": "THERE", "start": 0.4, "end": 0.9}]}]
    code, msg, _ = overlay.create_karaoke_captions(clip, segments, output_folder=str(tmp_path))
    assert code == 0, msg
    assert any(f.endswith(".mp4") for f in os.listdir(tmp_path))


def test_karaoke_needs_word_timestamps(clip, tmp_path):
    code, _, _ = overlay.create_karaoke_captions(clip, [{"text": "no words"}], output_folder=str(tmp_path))
    assert code != 0


def test_missing_video(tmp_path):
    code, _, _ = overlay.create_text_overlay(str(tmp_path / "nope.mp4"), "X")
    assert code != 0
