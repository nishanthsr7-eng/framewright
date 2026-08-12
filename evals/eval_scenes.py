"""Scene-cut precision / recall / F1 against the known cuts in evals/fixtures/cuts.mp4.

A detected cut matches a true cut within one frame (each true cut used once).
Usage: uv run --directory servers/analysis/scene_detector python ../../../evals/eval_scenes.py
"""
from __future__ import annotations

import json
from pathlib import Path

from scene_detector_mcp.detector import detect_scenes

FIX = Path(__file__).resolve().parent / "fixtures"


def prf(detected: list[float], truth: list[float], tol: float) -> tuple[float, float, float]:
    left, hits = list(truth), 0
    for d in detected:
        near = [t for t in left if abs(t - d) <= tol]
        if near:
            left.remove(min(near, key=lambda t: abs(t - d)))
            hits += 1
    p = hits / len(detected) if detected else 0.0
    r = hits / len(truth) if truth else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def main() -> None:
    truth = json.loads((FIX / "ground_truth.json").read_text())["video"]
    print("| video | true cuts | detected | precision | recall | F1 |")
    print("|---|---|---|---|---|---|")
    for name, gt in truth.items():
        scenes = detect_scenes(str(FIX / name))["scenes"]
        cuts = [s["start"] for s in scenes[1:]]
        p, r, f = prf(cuts, gt["cuts"], 1.0 / gt["fps"] + 1e-3)
        print(f"| {name} | {len(gt['cuts'])} | {len(cuts)} | {p:.3f} | {r:.3f} | {f:.3f} |")


if __name__ == "__main__":
    main()
