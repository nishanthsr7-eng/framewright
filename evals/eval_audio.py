"""Audio evals: beat F-measure (mir_eval, 70 ms window) and transcription WER (jiwer).

Uses the click tracks and speech.wav from evals/fixtures (run make_fixtures.py first).
Usage: uv run --directory servers/analysis/audio_analyzer --with mir_eval --with jiwer \
         python ../../../evals/eval_audio.py [--model base]
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import jiwer
import mir_eval
import numpy as np
from audio_analyzer_mcp.analyzer import detect_beats, transcribe_audio

FIX = Path(__file__).resolve().parent / "fixtures"


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9' ]+", " ", text.lower()).split())


def main() -> None:
    truth = json.loads((FIX / "ground_truth.json").read_text())
    model = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "base"

    print("| track | true BPM | detected BPM | beat F-measure |")
    print("|---|---|---|---|")
    for name, gt in truth["audio"].items():
        res = detect_beats(str(FIX / name))
        f = mir_eval.beat.f_measure(np.array(gt["beats"]), np.array(res["beat_times"]))
        print(f"| {name} | {gt['bpm']} | {res['tempo_bpm']} | {f:.3f} |")

    if not truth.get("speech"):
        print("\nno speech fixture; WER skipped", file=sys.stderr)
        return
    print("\n| clip | whisper model | WER | seconds |")
    print("|---|---|---|---|")
    for name, gt in truth["speech"].items():
        t0 = time.perf_counter()
        res = transcribe_audio(str(FIX / name), model_size=model, language="en", word_timestamps=False)
        dt = time.perf_counter() - t0
        hyp = " ".join(s["text"] for s in res["segments"])
        wer = jiwer.wer(_norm(gt["text"]), _norm(hyp))
        print(f"| {name} | {model} | {wer:.3f} | {dt:.1f} |")


if __name__ == "__main__":
    main()
