"""Beat-sync accuracy: how far each cut in the output lands from the true beat.

Cuts alternate between a red and a blue clip, so every cut is an exact colour
flip we can find frame by frame. Errors are measured against the known beats in
evals/fixtures/ground_truth.json (run make_fixtures.py first).

Usage: uv run --directory servers/analysis/beat_sync python ../../../evals/eval_beat_sync.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from beat_sync_mcp.beat_sync import generate_beat_synced_video

FIX = Path(__file__).resolve().parent / "fixtures"
FPS = 25


def solid(path: Path, color: str) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:size=320x180:rate={FPS}",
            "-t",
            "30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        timeout=120,
    )


def cut_times(video: Path) -> list[float]:
    raw = subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            "scale=1:1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-",
        ],
        capture_output=True,
        check=True,
        timeout=300,
    ).stdout
    red = [raw[i] > raw[i + 2] for i in range(0, len(raw), 3)]
    return [i / FPS for i in range(1, len(red)) if red[i] != red[i - 1]]


def main() -> None:
    truth = json.loads((FIX / "ground_truth.json").read_text())["audio"]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        red, blue = Path(tmp, "red.mp4"), Path(tmp, "blue.mp4")
        solid(red, "red")
        solid(blue, "blue")
        for name, gt in truth.items():
            out = Path(tmp, f"{name}.mp4")
            generate_beat_synced_video([str(red), str(blue)], str(FIX / name), str(out))
            errs = [min(abs(c - b) for b in gt["beats"]) * 1000 for c in cut_times(out)]
            off = sum(e > 1000 / FPS for e in errs)
            rows.append((name, len(errs), off, sum(errs) / len(errs), max(errs)))
    print("| track | cuts | >1 frame off | mean ms | worst ms |")
    print("|---|---|---|---|---|")
    for r in rows:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]:.1f} | {r[4]:.1f} |")
    tot, off = sum(r[1] for r in rows), sum(r[2] for r in rows)
    print(f"\ntotal: {off}/{tot} cuts more than one frame ({1000 / FPS:.0f} ms) off", file=sys.stderr)
    if off:
        sys.exit(1)  # CI gate: every cut must land within one frame of a beat


if __name__ == "__main__":
    main()
