"""Static checks for the Resolve Lua scripts (no Lua interpreter needed)."""

import re
from pathlib import Path

import pytest
from lua_source import code_only

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = sorted((ROOT / "resolve" / "scripts").rglob("*.lua"))


def _words(src, word):
    return len(re.findall(rf"\b{word}\b", src))


def test_scripts_exist():
    assert len(SCRIPTS) >= 20


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_blocks_are_balanced(path):
    code = code_only(path.read_text(encoding="utf-8"))
    opened = _words(code, "function") + _words(code, "if") + _words(code, "do")
    assert opened == _words(code, "end"), "function/if/do vs end mismatch"
    assert _words(code, "repeat") == _words(code, "until")
    for a, b in ("()", "{}", "[]"):
        assert code.count(a) == code.count(b), f"unbalanced {a}{b}"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_scripts_use_resolve_api(path):
    src = path.read_text(encoding="utf-8")
    assert src.lstrip().startswith("--"), "script should start with a comment describing it"
    assert "resolve" in src
