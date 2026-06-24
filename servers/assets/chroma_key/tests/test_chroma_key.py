import json
import subprocess

import pytest

np = pytest.importorskip("numpy")
chroma = pytest.importorskip("chroma_key_mcp.chroma")


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def _first_frame_rgb(path, w, h):
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return np.frombuffer(out.stdout, dtype=np.uint8).reshape(h, w, 3)


def test_remove_background_writes_alpha_webm(media, tmp_path):
    out = str(tmp_path / "keyed.webm")
    res = chroma.remove_background(media["fg"], output_path=out)
    assert res["output_path"] == out and res["color"] == "0x00FF00"
    stream = _probe(out)["streams"][0]
    assert stream["codec_name"] == "vp9"
    assert stream.get("tags", {}).get("alpha_mode", stream.get("tags", {}).get("ALPHA_MODE")) == "1"


def test_replace_background_with_image(media, tmp_path):
    out = str(tmp_path / "replaced.mp4")
    chroma.replace_background(media["fg"], media["bg"], output_path=out)
    info = _probe(out)
    assert float(info["format"]["duration"]) == pytest.approx(1.0, abs=0.1)
    frame = _first_frame_rgb(out, 160, 120).astype(int)
    corner, center = frame[5, 5], frame[60, 80]
    assert corner[2] > 200 and corner[1] < 60  # green replaced by blue
    assert center[0] > 200 and center[1] < 60  # red box kept


def test_missing_input_raises(media, tmp_path):
    with pytest.raises(FileNotFoundError):
        chroma.remove_background(str(tmp_path / "nope.mp4"))
    with pytest.raises(FileNotFoundError):
        chroma.replace_background(media["fg"], str(tmp_path / "nope.png"))
