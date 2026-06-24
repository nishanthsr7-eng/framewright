import hashlib
import importlib.util
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def fm():
    spec = importlib.util.spec_from_file_location("fetch_models", ROOT / "scripts" / "fetch_models.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_models_live_under_models_dir(fm):
    for spec in fm.MODELS_SPEC.values():
        assert fm.MODELS in Path(spec["dest"]).parents
        assert spec["url"].startswith("https://")


def test_sha256(fm, tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"framewright")
    assert fm._sha256(f) == hashlib.sha256(b"framewright").hexdigest()


def test_unzip_strips_single_top_folder(fm, tmp_path):
    z = tmp_path / "a.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("pkg/bin/tool", "x")
        zf.writestr("pkg/models/m.param", "y")
    fm._flatten_unzip(z, tmp_path / "out")
    assert (tmp_path / "out" / "bin" / "tool").read_text() == "x"
    assert (tmp_path / "out" / "models" / "m.param").exists()


def test_unzip_rejects_path_traversal(fm, tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../escape.txt", "x")
        zf.writestr("ok.txt", "y")
    with pytest.raises(RuntimeError):
        fm._flatten_unzip(z, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()


def test_fetch_skips_existing_file(fm, tmp_path, monkeypatch):
    dest = tmp_path / "m.onnx"
    dest.write_bytes(b"x")
    monkeypatch.setattr(fm, "ROOT", tmp_path)
    monkeypatch.setitem(fm.MODELS_SPEC, "fake", {"desc": "", "url": "https://invalid", "dest": dest, "sha256": None})
    monkeypatch.setattr(fm, "_download", lambda *a: pytest.fail("should not download"))
    assert fm.fetch("fake", force=False) is True
