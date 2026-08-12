"""Generate synthetic, license-free eval fixtures with known ground truth.

Outputs (in evals/fixtures/, gitignored):
  click_<bpm>.wav        click track, beats at known times
  cuts.mp4               video of solid/pattern shots with known cut times
  ground_truth.json      beat and cut times for every fixture

Usage: python evals/make_fixtures.py   (needs ffmpeg on PATH)
"""
from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parent / "fixtures"
SR = 44100


def click_track(path: Path, bpm: float, seconds: float, offset: float = 0.5) -> list[float]:
    """Write a mono WAV with a 1 kHz click on every beat (accent on downbeats)."""
    n = int(SR * seconds)
    samples = [0.0] * n
    beats, t, i = [], offset, 0
    click_len = int(SR * 0.03)
    while t < seconds - 0.05:
        start = int(round(t * SR))
        freq, amp = (1500.0, 0.9) if i % 4 == 0 else (1000.0, 0.6)
        for k in range(click_len):
            if start + k < n:
                env = math.exp(-k / (SR * 0.005))
                samples[start + k] = amp * env * math.sin(2 * math.pi * freq * k / SR)
        beats.append(round(t, 4))
        t += 60.0 / bpm
        i += 1
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in samples))
    return beats


def cut_video(path: Path, shots: list[tuple[str, float]], fps: int = 25) -> list[float]:
    """Concat lavfi shots (source, duration) with hard cuts; return cut times."""
    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for src, dur in shots:
        args += ["-f", "lavfi", "-t", str(dur), "-i", f"{src}{':' if '=' in src else '='}size=640x360:rate={fps}"]
    chain = "".join(f"[{i}:v]" for i in range(len(shots)))
    args += ["-filter_complex", f"{chain}concat=n={len(shots)}:v=1:a=0[v]",
             "-map", "[v]", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(args, check=True, timeout=120)
    cuts, t = [], 0.0
    for _, dur in shots[:-1]:
        t += dur
        cuts.append(round(t, 4))
    return cuts


SPEECH = ("The quick brown fox jumps over the lazy dog. "
          "Every frame of this video was cut on the beat of the music. "
          "Open the timeline, add a title, and render the final edit at sixty frames per second.")


def speech(path: Path, text: str) -> bool:
    """Synthesize speech with the OS voice (SAPI / say / espeak-ng). Returns False if none is available."""
    if sys.platform == "win32":
        ps = ("Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              f"$s.SetOutputToWaveFile('{path}'); $s.Speak('{text}'); $s.Dispose()")
        args = ["powershell", "-NoProfile", "-Command", ps]
    elif sys.platform == "darwin":
        args = ["say", "-o", str(path), "--data-format=LEI16@22050", text]
    else:
        args = ["espeak-ng", "-w", str(path), text]
    try:
        subprocess.run(args, check=True, timeout=120, capture_output=True)
        return path.exists()
    except (OSError, subprocess.CalledProcessError):
        return False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    truth: dict = {"audio": {}, "video": {}}
    for bpm in (90, 120, 140):
        name = f"click_{bpm}.wav"
        truth["audio"][name] = {"bpm": bpm, "beats": click_track(OUT / name, bpm, 20.0)}
    shots = [
        ("color=c=red", 2.0), ("testsrc", 3.0), ("color=c=blue", 1.5),
        ("mandelbrot", 2.5), ("color=c=green", 2.0), ("smptebars", 3.0),
    ]
    truth["video"]["cuts.mp4"] = {"fps": 25, "cuts": cut_video(OUT / "cuts.mp4", shots)}
    truth["speech"] = {}
    if speech(OUT / "speech.wav", SPEECH):
        truth["speech"]["speech.wav"] = {"text": SPEECH}
    else:
        print("no OS text-to-speech found; skipping speech.wav (WER eval)", file=sys.stderr)
    (OUT / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    print(f"fixtures written to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
