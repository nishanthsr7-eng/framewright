"""Pull evenly spaced frames from your own clips for hand labeling (see evals/LABELING.md).

Put clips in samples/anime/ and samples/live-action/ (both gitignored).
Writes evals/labels/<set>/images/<name>.png (gitignored).
Usage: python evals/extract_label_frames.py [--per-set 20]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LABELS = ROOT / "evals" / "labels"
SAMPLES = ROOT / "samples"
SETS = ("anime", "live-action")
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm"}


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True, timeout=30)
    return float(out.stdout.strip())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-set", type=int, default=20, help="frames per set, split across its clips")
    args = ap.parse_args()
    for name in SETS:
        clips = sorted(p for p in (SAMPLES / name).glob("*") if p.suffix.lower() in VIDEO_EXTS)
        if not clips:
            print(f"{name}: no clips in {SAMPLES / name}, skipped", file=sys.stderr)
            continue
        out_dir = LABELS / name / "images"
        out_dir.mkdir(parents=True, exist_ok=True)
        for i, path in enumerate(clips):
            count = args.per_set // len(clips) + (i < args.per_set % len(clips))
            d = duration(path)
            for k in range(count):
                t = d * (0.05 + 0.9 * (k + 0.5) / count)  # skip intro/outro
                dst = out_dir / f"{path.stem}_{t:07.2f}s.png"
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(path),
                                "-frames:v", "1", str(dst)], check=True, timeout=60)
        print(f"{name}: {len(list(out_dir.glob('*.png')))} frames in {out_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
