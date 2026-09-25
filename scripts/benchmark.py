"""Time the heavy tools in seconds per minute of 1080p footage, on CPU and GPU where both exist.

Uses a synthetic 1080p clip (testsrc2) so no footage is needed. Frame-based tools run on --frames
frames and are scaled up to one minute at --fps. Whisper runs on evals/fixtures/speech.wav
(run evals/make_fixtures.py first) and is scaled by its length. Model load time is excluded.

Usage: uv run python scripts/benchmark.py [--frames 24] [--fps 24] [--only subject whisper esrgan stabilize]
Prints a markdown table; tools that can't run (missing model, no GPU) show the reason.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ["subject", "whisper", "esrgan", "stabilize"]


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True, timeout=600)


def make_inputs(tmp: Path, frames: int, fps: int) -> tuple[Path, Path]:
    clip = tmp / "clip.mp4"
    ffmpeg(
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size=1920x1080:rate={fps}",
        "-frames:v",
        str(frames),
        "-pix_fmt",
        "yuv420p",
        str(clip),
    )
    frames_dir = tmp / "frames"
    frames_dir.mkdir()
    ffmpeg("-i", str(clip), str(frames_dir / "frame_%04d.png"))
    return clip, frames_dir


def per_minute(seconds: float, frames: int, fps: int) -> float:
    return seconds / (frames / fps) * 60


def bench_subject(frames_dir: Path, frames: int, fps: int, rows: list) -> None:
    import onnxruntime as ort
    from subject_extractor_mcp import segmenter

    files = sorted(frames_dir.iterdir())
    out = frames_dir.parent / "subject"
    out.mkdir(exist_ok=True)
    gpu = [p for p in ort.get_available_providers() if p in ("CUDAExecutionProvider", "DmlExecutionProvider")]
    auto = segmenter._providers
    for style in ("anime", "general", "general_hq"):
        for device in ("GPU", "CPU"):
            if device == "GPU" and not gpu:
                rows.append((f"subject extraction ({style})", device, None, "no GPU provider"))
                continue
            segmenter._sessions.clear()
            segmenter._providers = auto if device == "GPU" else (lambda: ["CPUExecutionProvider"])
            try:
                segmenter.split_subject_and_background(str(files[0]), str(out / "warm.png"), style=style)  # load
                t = time.perf_counter()
                for f in files:
                    segmenter.split_subject_and_background(str(f), str(out / f.name), style=style)
                rows.append(
                    (f"subject extraction ({style})", device, per_minute(time.perf_counter() - t, frames, fps), "")
                )
            except FileNotFoundError as e:
                rows.append((f"subject extraction ({style})", device, None, str(e).split(".")[0]))
                break
    segmenter._providers = auto


def bench_whisper(rows: list) -> None:
    import ctranslate2
    import librosa
    from audio_analyzer_mcp import analyzer
    from faster_whisper import WhisperModel

    speech = ROOT / "evals" / "fixtures" / "speech.wav"
    if not speech.exists():
        rows.append(("Whisper base (transcription)", "-", None, "run evals/make_fixtures.py first"))
        return
    seconds = librosa.get_duration(path=str(speech))
    for device, compute in (("GPU", "float16"), ("CPU", "int8")):
        if device == "GPU" and ctranslate2.get_cuda_device_count() == 0:
            rows.append(("Whisper base (transcription)", device, None, "no CUDA device"))
            continue
        try:
            analyzer._WHISPER_MODELS["base"] = WhisperModel(
                "base", device=device.lower().replace("gpu", "cuda"), compute_type=compute
            )
            analyzer.transcribe_audio(str(speech))  # warm-up
            t = time.perf_counter()
            analyzer.transcribe_audio(str(speech))
            rows.append(
                (
                    "Whisper base (transcription)",
                    device,
                    (time.perf_counter() - t) / seconds * 60,
                    "per minute of audio",
                )
            )
        except Exception as e:
            rows.append(("Whisper base (transcription)", device, None, f"{type(e).__name__}: {e}"[:80]))
    analyzer._WHISPER_MODELS.clear()


def bench_esrgan(frames_dir: Path, frames: int, fps: int, rows: list) -> None:
    from ffmpeg_mcp import cut_video

    out = frames_dir.parent / "esrgan"
    t = time.perf_counter()
    code, log, _ = cut_video.enhance_frames(str(frames_dir), str(out), model="realesr-animevideov3", scale=2)
    if code != 0:
        rows.append(("Real-ESRGAN x2 (animevideov3)", "GPU (Vulkan)", None, log.strip().splitlines()[-1][:80]))
        return
    rows.append(
        (
            "Real-ESRGAN x2 (animevideov3)",
            "GPU (Vulkan)",
            per_minute(time.perf_counter() - t, frames, fps),
            "includes model load",
        )
    )
    rows.append(("Real-ESRGAN", "CPU", None, "ncnn-vulkan build is GPU only"))


def bench_stabilize(clip: Path, frames: int, fps: int, rows: list) -> None:
    from stabilization_mcp.stabilize import stabilize_video

    t = time.perf_counter()
    stabilize_video(str(clip), output_path=str(clip.with_name("stab.mp4")))
    rows.append(
        ("stabilization (vid.stab, 2 passes)", "CPU", per_minute(time.perf_counter() - t, frames, fps), "ffmpeg only")
    )
    rows.append(("stabilization", "GPU", None, "no GPU path"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", type=int, default=24, help="frames to time (more = steadier numbers)")
    ap.add_argument("--fps", type=int, default=24, help="frame rate used to scale to one minute")
    ap.add_argument("--only", nargs="+", choices=TOOLS, default=TOOLS)
    args = ap.parse_args()

    rows: list = []
    with tempfile.TemporaryDirectory() as t:
        clip, frames_dir = make_inputs(Path(t), args.frames, args.fps)
        steps = {
            "subject": lambda: bench_subject(frames_dir, args.frames, args.fps, rows),
            "whisper": lambda: bench_whisper(rows),
            "esrgan": lambda: bench_esrgan(frames_dir, args.frames, args.fps, rows),
            "stabilize": lambda: bench_stabilize(clip, args.frames, args.fps, rows),
        }
        for name in args.only:
            print(f"benchmarking {name}...", file=sys.stderr, flush=True)
            try:
                steps[name]()
            except ImportError as e:
                rows.append((name, "-", None, f"not installed: {e.name}"))

    print(
        f"Seconds per minute of 1080p footage at {args.fps} fps ({args.frames} frames timed, {os.cpu_count()} CPU threads).\n"
    )
    print("| tool | device | s / min | note |")
    print("|---|---|---|---|")
    for tool, device, s, note in rows:
        print(f"| {tool} | {device} | {f'{s:.0f}' if s is not None else '-'} | {note} |")


if __name__ == "__main__":
    main()
