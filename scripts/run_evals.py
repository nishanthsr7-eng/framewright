"""Run the evals from the repo root, each inside the server environment it tests.

Usage:
  python scripts/run_evals.py                 # fixtures + beat_sync + scenes (what CI runs)
  python scripts/run_evals.py all             # also audio (beats F-measure, WER) and segmentation
  python scripts/run_evals.py segmentation -- --hq
Exits non-zero if any eval fails.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# name -> (workspace package, extra --with deps, script)
EVALS = {
    "beat_sync": ("beat-sync-mcp", [], "eval_beat_sync.py"),
    "scenes": ("scene-detector-mcp", [], "eval_scenes.py"),
    "audio": ("audio-analyzer-mcp", ["mir_eval", "jiwer"], "eval_audio.py"),
    "segmentation": ("subject-extractor-mcp", [], "eval_segmentation.py"),
}
DEFAULT = ["beat_sync", "scenes"]


def run(cmd: list[str]) -> int:
    print("$ " + " ".join(cmd), file=sys.stderr, flush=True)
    return subprocess.run(cmd, cwd=ROOT, timeout=3600).returncode


def main() -> None:
    argv = sys.argv[1:]
    extra = argv[argv.index("--") + 1 :] if "--" in argv else []
    names = argv[: argv.index("--")] if "--" in argv else argv
    if names == ["all"]:
        names = list(EVALS)
    names = names or DEFAULT
    unknown = [n for n in names if n not in EVALS]
    if unknown:
        sys.exit(f"unknown eval(s): {', '.join(unknown)}. Choose from: {', '.join(EVALS)} or 'all'")

    if run([sys.executable, "evals/make_fixtures.py"]) != 0:
        sys.exit("make_fixtures.py failed")
    failed = []
    for name in names:
        pkg, withs, script = EVALS[name]
        cmd = ["uv", "run", "--package", pkg] + [a for w in withs for a in ("--with", w)]
        if run(cmd + ["python", f"evals/{script}"] + extra) != 0:
            failed.append(name)
    if failed:
        sys.exit(f"failed: {', '.join(failed)}")


if __name__ == "__main__":
    main()
