"""Static checks for the Fusion .setting templates."""

from pathlib import Path

import pytest
from lua_source import code_only

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = sorted((ROOT / "resolve" / "templates").rglob("*.setting"))


def test_templates_exist():
    kinds = {p.parent.name for p in TEMPLATES}
    assert {"Effects", "Transitions"} <= kinds


def test_template_names_are_unique():
    names = [p.stem for p in TEMPLATES]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.relative_to(ROOT).as_posix())
def test_template_is_a_balanced_table(path):
    src = code_only(path.read_text(encoding="utf-8", errors="replace")).strip()
    assert src.startswith("{") and src.endswith("}")
    depth = 0
    for ch in src:
        depth += {"{": 1, "}": -1}.get(ch, 0)
        assert depth >= 0
    assert depth == 0
    assert "Tools = ordered()" in src or "Tools =" in src
