import logging
import os
import shutil
import sys

import pytest

core = pytest.importorskip("framewright_core")
ToolError = pytest.importorskip("mcp.server.fastmcp.exceptions").ToolError


def test_servers_dir_from_package():
    found = core.servers_dir()
    assert found is not None and os.path.basename(found) == "servers"
    assert os.path.isdir(os.path.join(found, "core"))


def test_servers_dir_outside_repo(tmp_path):
    assert core.servers_dir(str(tmp_path)) is None


def test_output_root_is_repo_output():
    assert core.output_root() == os.path.join(os.path.dirname(core.servers_dir()), "output")


def test_output_root_outside_repo(tmp_path):
    assert core.output_root(str(tmp_path)) == os.path.join(str(tmp_path), "output")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
def test_run_ffmpeg_success_and_failure(tmp_path):
    out = tmp_path / "x.wav"
    core.run_ffmpeg(["-v", "error", "-f", "lavfi", "-i", "sine=duration=0.1", str(out)], timeout=60)
    assert out.stat().st_size > 0
    with pytest.raises(RuntimeError, match="ffmpeg failed"):
        core.run_ffmpeg(["-i", str(tmp_path / "missing.mp4"), str(tmp_path / "y.mp4")], timeout=60)


def test_run_tool_passes_result_through():
    assert core.run_tool(lambda a, b=0: {"sum": a + b}, 1, b=2) == {"sum": 3}


@pytest.mark.parametrize(
    "exc, fragment",
    [(FileNotFoundError("nope.mp4"), "Check the path exists"), (ValueError("bad"), "bad"), (KeyError("k"), "KeyError")],
)
def test_run_tool_maps_errors(exc, fragment):
    def boom():
        raise exc

    with pytest.raises(ToolError, match=fragment):
        core.run_tool(boom)


def test_setup_logging_uses_stderr(monkeypatch):
    calls = {}
    monkeypatch.setattr(logging, "basicConfig", lambda **kw: calls.update(kw))
    core.setup_logging()
    assert calls["stream"] is sys.stderr
