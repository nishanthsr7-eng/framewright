"""Scene-cut precision / recall / F1 against the known cuts in evals/fixtures/ (cuts.mp4, cuts_hard.mp4).

A detected cut matches a true cut within one frame, or within that cut's "tol" for dissolves
(each true cut used once). Only fixtures without "gate": false fail CI.
Usage: uv run --directory servers/analysis/scene_detector python ../../../evals/eval_scenes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from scene_detector_mcp.detector import detect_scenes

FIX = Path(__file__).resolve().parent / "fixtures"


def prf(detected: list[float], truth: list[float], tol: float | list[float]) -> tuple[float, float, float]:
    tols = tol if isinstance(tol, list) else [tol] * len(truth)
    left, hits = list(zip(truth, tols, strict=True)), 0
    for d in detected:
        near = [(t, w) for t, w in left if abs(t - d) <= w]
        if near:
            left.remove(min(near, key=lambda tw: abs(tw[0] - d)))
            hits += 1
    p = hits / len(detected) if detected else 0.0
    r = hits / len(truth) if truth else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main() -> None:
    truth = json.loads((FIX / "ground_truth.json").read_text())["video"]
    print("| video | true cuts | detected | precision | recall | F1 |")
    print("|---|---|---|---|---|---|")
    failed = False
    for name, gt in truth.items():
        scenes = detect_scenes(str(FIX / name))["scenes"]
        cuts = [s["start"] for s in scenes[1:]]
        p, r, f = prf(cuts, gt["cuts"], gt.get("tol", 1.0 / gt["fps"] + 1e-3))
        print(f"| {name} | {len(gt['cuts'])} | {len(cuts)} | {p:.3f} | {r:.3f} | {f:.3f} |")
        if gt.get("gate", True):
            failed |= p < 1.0 or r < 1.0
    if failed:
        sys.exit(1)  # CI gate: synthetic cuts must be found exactly


if __name__ == "__main__":
    main()
