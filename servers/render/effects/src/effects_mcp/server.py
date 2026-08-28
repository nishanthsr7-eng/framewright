import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from effects_mcp import effects

setup_logging()
mcp = FastMCP("effects-mcp")

# Grain, vignette and light leaks live in overlay-fx; speed in speed-ramp; colour grades in lut-grading.
Effect = Literal["zoom_punch", "shake", "rgb_split", "flash", "glow"]
Transition = Literal[tuple(effects.TRANSITIONS)]


@mcp.tool()
def apply_effect(
    video_path: Annotated[str, Field(description="Source video")],
    effect: Annotated[
        Effect,
        Field(
            description="zoom_punch: quick zoom hit; shake: impact shake; rgb_split: glitchy colour split; flash: white flash; glow: soft bloom"
        ),
    ],
    intensity: Annotated[float, Field(ge=0.1, le=3, description="About 0.5 subtle to 2 strong")] = 1.0,
    start_time: Annotated[float, Field(ge=0, description="Effect start in seconds")] = 0.0,
    duration: Annotated[
        float | None, Field(gt=0, description="Effect length in seconds; default is to the end")
    ] = None,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_<effect>.<ext>")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Apply a punchy edit effect to a time range of a video. Frames outside the range are unchanged."""
    return _run(
        effects.apply_effect,
        video_path,
        effect,
        intensity=intensity,
        start_time=start_time,
        duration=duration,
        output_path=output_path,
        lossless=lossless,
    )


@mcp.tool()
def apply_transition(
    video_a: Annotated[str, Field(description="First clip")],
    video_b: Annotated[str, Field(description="Second clip; scaled to match the first")],
    transition: Annotated[
        Transition,
        Field(description="ffmpeg xfade transition, e.g. fade, dissolve, wipeleft, slideup, circleopen, zoomin"),
    ] = "fade",
    duration: Annotated[float, Field(gt=0, le=5, description="Transition length in seconds")] = 0.5,
    output_path: Annotated[str | None, Field(description="Default: output/<a>/<a>_<transition>_transition.mp4")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Join two clips with a transition between them."""
    return _run(
        effects.apply_transition,
        video_a,
        video_b,
        transition=transition,
        duration=duration,
        output_path=output_path,
        lossless=lossless,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
