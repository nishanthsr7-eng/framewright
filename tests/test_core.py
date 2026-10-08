import os

import pytest
from framewright_core import default_output_path, output_root, run_tool, servers_dir, video_codec_args
from framewright_core import paths as core_paths
from mcp.server.fastmcp.exceptions import ToolError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_servers_dir_found_from_inside_repo():
    start = os.path.join(REPO, "servers", "render", "effects", "src")
    assert servers_dir(start) == os.path.join(REPO, "servers")


def test_servers_dir_none_outside_repo(tmp_path):
    assert servers_dir(str(tmp_path)) is None


def test_output_root_inside_repo_is_repo_output():
    assert output_root(os.path.join(REPO, "servers", "core")) == os.path.join(REPO, "output")


def test_output_root_outside_repo_is_next_to_start(tmp_path):
    assert output_root(str(tmp_path)) == os.path.join(str(tmp_path), "output")


@pytest.fixture
def out_root(tmp_path, monkeypatch):
    monkeypatch.setattr(core_paths, "output_root", lambda start=None: str(tmp_path))
    return tmp_path


def test_default_output_path_keeps_input_ext(out_root):
    p = default_output_path("/videos/clip.mov", "graded")
    assert p == os.path.join(str(out_root), "clip", "clip_graded.mov")
    assert os.path.isdir(os.path.dirname(p))


def test_default_output_path_ext_override_and_fallback(out_root):
    assert default_output_path("a/clip.mp4", "keyed", ext=".webm").endswith("clip_keyed.webm")
    assert default_output_path("a/noext", "x").endswith("noext_x.mp4")
    assert default_output_path("a/noext", "x", default_ext=".wav").endswith("noext_x.wav")


def test_video_codec_args_default_is_lossy_h264():
    args = video_codec_args()
    assert args[:2] == ["-c:v", "libx264"] and "-qp" not in args and "yuv420p" in args


def test_video_codec_args_lossless_uses_qp0():
    args = video_codec_args(True)
    assert args[args.index("-qp") + 1] == "0"


def test_run_tool_passes_result_through():
    assert run_tool(lambda a, b=0: {"sum": a + b}, 2, b=3) == {"sum": 5}


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (FileNotFoundError("missing.mp4"), "Check the path exists"),
        (ValueError("bad value"), "bad value"),
        (RuntimeError("ffmpeg failed"), "ffmpeg failed"),
        (KeyError("k"), "KeyError"),
    ],
)
def test_run_tool_maps_errors_to_tool_error(exc, expected):
    def boom():
        raise exc

    with pytest.raises(ToolError, match=expected) as info:
        run_tool(boom)
    assert info.value.__cause__ is exc
