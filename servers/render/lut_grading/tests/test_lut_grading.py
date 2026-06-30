import json
import os
import subprocess

import pytest

np = pytest.importorskip("numpy")
grading = pytest.importorskip("lut_grading_mcp.grading")


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


def _mid_frame_rgb(path):
    out = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            "0.5",
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


@pytest.mark.parametrize("name", sorted(grading.BUILTIN_LUTS))
def test_builtin_cube_files_are_valid(name):
    path = grading.list_luts()[name]["path"]
    with open(path) as f:
        lines = [ln.split() for ln in f if ln.strip() and not ln.startswith("#")]
    size = int(next(ln[1] for ln in lines if ln[0] == "LUT_3D_SIZE"))
    rows = [ln for ln in lines if len(ln) == 3 and ln[0][0].isdigit()]
    assert len(rows) == size**3
    assert all(0.0 <= float(v) <= 1.0 for row in rows for v in row)


def test_apply_lut_keeps_audio(media, tmp_path):
    out = str(tmp_path / "graded.mp4")
    res = grading.apply_lut(media["av"], "cool_blue", output_path=out)
    assert res == {"output_path": out, "lut": "cool_blue", "intensity": 1.0}
    assert {s["codec_type"] for s in _probe(out)["streams"]} == {"video", "audio"}


def test_black_and_white_lut_removes_color(media, tmp_path):
    out = str(tmp_path / "bw.mp4")
    grading.apply_lut(media["v"], "high_contrast_bw", output_path=out)
    rgb = _mid_frame_rgb(out)
    assert np.abs(rgb[..., 0] - rgb[..., 2]).mean() < 8


def test_partial_intensity_blends(media, tmp_path):
    full, half = str(tmp_path / "full.mp4"), str(tmp_path / "half.mp4")
    grading.apply_lut(media["av"], "high_contrast_bw", output_path=full)
    res = grading.apply_lut(media["av"], "high_contrast_bw", intensity=0.5, output_path=half)
    assert res["intensity"] == 0.5
    orig, a, b = _mid_frame_rgb(media["av"]), _mid_frame_rgb(full), _mid_frame_rgb(half)
    assert np.abs(b - orig).mean() < np.abs(a - orig).mean()


def test_intensity_is_clamped(media, tmp_path):
    res = grading.apply_lut(media["v"], "faded_film", intensity=3, output_path=str(tmp_path / "x.mp4"))
    assert res["intensity"] == 1.0


def test_custom_cube_path(media, tmp_path):
    cube = grading.list_luts()["warm_vintage"]["path"]
    out = str(tmp_path / "custom.mp4")
    grading.apply_lut(media["v"], cube, output_path=out)
    assert os.path.getsize(out) > 0


def test_unknown_lut_raises(media):
    with pytest.raises(FileNotFoundError):
        grading.apply_lut(media["v"], "not_a_lut")
