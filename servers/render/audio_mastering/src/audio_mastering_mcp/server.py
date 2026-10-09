import sys
from typing import Annotated

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from audio_mastering_mcp import mastering

setup_logging()
mcp = FastMCP("audio-mastering-mcp")

InputPath = Annotated[str, Field(description="Audio or video file")]


@mcp.tool()
def normalize_loudness(
    input_path: InputPath,
    target_lufs: Annotated[
        float, Field(ge=-40, le=-5, description="-14 streaming/YouTube, -16 podcasts, -23 broadcast")
    ] = -14.0,
    output_path: Annotated[str | None, Field(description="Default: output/<file>/<file>_normalized.<ext>")] = None,
) -> dict:
    """Normalise loudness to a target LUFS (EBU R128)."""
    return _run(mastering.normalize_loudness, input_path, target_lufs=target_lufs, output_path=output_path)


@mcp.tool()
def reduce_noise(
    input_path: InputPath,
    amount: Annotated[float, Field(ge=0.01, le=97, description="Reduction in dB; too high sounds watery")] = 12,
    output_path: Annotated[str | None, Field(description="Default: output/<file>/<file>_denoised.<ext>")] = None,
) -> dict:
    """Remove steady background hiss or hum."""
    return _run(mastering.reduce_noise, input_path, amount=amount, output_path=output_path)


@mcp.tool()
def add_background_music(
    video_path: Annotated[str, Field(description="Source video")],
    music_path: Annotated[str, Field(description="Music file")],
    music_volume_db: Annotated[float, Field(ge=-60, le=12, description="Music gain in dB")] = -20.0,
    duck: Annotated[bool, Field(description="Lower the music while the video's own audio is loud")] = True,
    duck_threshold_db: Annotated[float, Field(ge=-60, le=0, description="Level that triggers ducking")] = -30.0,
    duck_ratio: Annotated[float, Field(ge=1, le=20, description="Ducking compression ratio")] = 8.0,
    loop: Annotated[bool, Field(description="Loop the music if it is shorter than the video")] = True,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_with_music.<ext>")] = None,
) -> dict:
    """Mix background music under a video's audio, with optional ducking under speech."""
    return _run(
        mastering.add_background_music,
        video_path=video_path,
        music_path=music_path,
        music_volume_db=music_volume_db,
        duck=duck,
        duck_threshold_db=duck_threshold_db,
        duck_ratio=duck_ratio,
        loop=loop,
        output_path=output_path,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
