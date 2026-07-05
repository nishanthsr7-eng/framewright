import json
import os
import subprocess

import pytest

np = pytest.importorskip("numpy")
effects = pytest.importorskip("overlay_fx_mcp.effects")


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


def _frame(path, t=0.5):
    out = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            str(t),
            "-i",
            path,
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(120, 160, 3).astype(int)


@pytest.mark.parametrize("style", sorted(effects.LIGHT_LEAK_STYLES))
def test_light_leak_assets_exist(style):
    assert os.path.isfile(os.path.join(effects.ASSETS_DIR, f"{style}.png"))


def test_film_grain_changes_pixels_and_keeps_audio(media, tmp_path):
    out = str(tmp_path / "grain.mp4")
    res = effects.add_film_grain(media["av"], intensity=150, output_path=out)
    assert res["intensity"] == 100  # clamped
    assert np.abs(_frame(out) - _frame(media["av"])).mean() > 2
    assert {s["codec_type"] for s in _probe(out)["streams"]} == {"video", "audio"}


def test_vignette_darkens_corners(media, tmp_path):
    out = str(tmp_path / "vig.mp4")
    effects.add_vignette(media["v"], intensity=1.0, output_path=out)
    before, after = _frame(media["v"]), _frame(out)
    ring = np.ones((120, 160), dtype=bool)
    ring[20:-20, 20:-20] = False
    assert after[ring].mean() < before[ring].mean() - 5
    assert abs(after[50:70, 70:90].mean() - before[50:70, 70:90].mean()) < 10


def test_chromatic_aberration(media, tmp_path):
    out = str(tmp_path / "ca.mp4")
    assert effects.add_chromatic_aberration(media["v"], shift=4, output_path=out)["shift"] == 4
    assert _duration(out) == pytest.approx(1.0, abs=0.1)


@pytest.mark.parametrize("pan", sorted(effects.PAN_DIRECTIONS))
def test_light_leak_brightens(media, tmp_path, pan):
    out = str(tmp_path / f"leak_{pan}.mp4")
    res = effects.add_light_leak(media["av"], style="white", intensity=0.8, pan=pan, output_path=out)
    assert res["pan"] == pan
    assert _frame(out).mean() > _frame(media["av"]).mean()
    assert _duration(out) == pytest.approx(1.0, abs=0.1)


def test_light_leak_rejects_bad_options(media):
    with pytest.raises(ValueError):
        effects.add_light_leak(media["v"], style="purple")
    with pytest.raises(ValueError):
        effects.add_light_leak(media["v"], pan="diagonal")
