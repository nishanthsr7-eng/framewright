import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from audio_analyzer_mcp import analyzer

setup_logging()
mcp = FastMCP("audio-analyzer-mcp")

AudioPath = Annotated[str, Field(description="Audio or video file (the audio track is extracted)")]
Start = Annotated[float, Field(ge=0, description="Start of the analysed range, in seconds")]
Duration = Annotated[
    float | None, Field(gt=0, description="Length of the analysed range in seconds; default is to the end")
]


@mcp.tool()
def get_audio_info(audio_path: AudioPath) -> dict:
    """Duration, sample rate and overall loudness (RMS mean/max) of a file's audio."""
    return _run(analyzer.get_audio_info, audio_path)


@mcp.tool()
def detect_beats(audio_path: AudioPath, start_time: Start = 0.0, duration: Duration = None) -> dict:
    """Tempo (BPM) and beat times in seconds. Use for cutting or triggering effects on the beat."""
    return _run(analyzer.detect_beats, audio_path, start_time=start_time, duration=duration)


@mcp.tool()
def detect_downbeats(
    audio_path: AudioPath,
    start_time: Start = 0.0,
    duration: Duration = None,
    beats_per_bar: Annotated[int, Field(ge=2, le=12, description="Beats per bar (4 for 4/4 time)")] = 4,
) -> dict:
    """Downbeat (first beat of each bar) times. Sparser than beats; good for big cuts and transitions."""
    return _run(
        analyzer.detect_downbeats, audio_path, start_time=start_time, duration=duration, beats_per_bar=beats_per_bar
    )


@mcp.tool()
def detect_sections(
    audio_path: AudioPath,
    start_time: Start = 0.0,
    duration: Duration = None,
    n_sections: Annotated[
        int | None, Field(ge=2, le=16, description="Number of sections; default estimates from length (2-8)")
    ] = None,
) -> dict:
    """Split a song into labelled sections (intro/verse/build/drop/chorus/outro) with relative energy 0-1."""
    return _run(analyzer.detect_sections, audio_path, start_time=start_time, duration=duration, n_sections=n_sections)


@mcp.tool()
def detect_impacts(
    audio_path: AudioPath,
    start_time: Start = 0.0,
    duration: Duration = None,
    sensitivity: Annotated[float, Field(gt=0, le=5, description="Higher finds more impacts")] = 1.0,
) -> dict:
    """Transient hits (drums, impacts, sudden loudness) with strength 0-1. Use as effect or transition triggers."""
    return _run(analyzer.detect_impacts, audio_path, start_time=start_time, duration=duration, sensitivity=sensitivity)


@mcp.tool()
def analyze_audio_features(
    audio_path: AudioPath,
    start_time: Start = 0.0,
    duration: Duration = None,
    window: Annotated[float, Field(gt=0, le=30, description="Window length in seconds")] = 1.0,
) -> dict:
    """Per-window RMS energy, spectral centroid and zero-crossing rate, plus a summary. Finds loud or quiet parts."""
    return _run(analyzer.analyze_audio_features, audio_path, start_time=start_time, duration=duration, window=window)


@mcp.tool()
def transcribe_audio(
    audio_path: AudioPath,
    model_size: Annotated[
        Literal["tiny", "base", "small", "medium", "large-v3"],
        Field(description="Whisper model; larger is slower and more accurate"),
    ] = "base",
    language: Annotated[str | None, Field(description="Language code such as 'en'; default auto-detects")] = None,
    word_timestamps: Annotated[bool, Field(description="Include per-word timings")] = True,
) -> dict:
    """Transcribe speech locally with faster-whisper. Returns text and timed segments for captions.
    The model downloads on first use of each size."""
    return _run(
        analyzer.transcribe_audio, audio_path, model_size=model_size, language=language, word_timestamps=word_timestamps
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
