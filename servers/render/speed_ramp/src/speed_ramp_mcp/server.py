import sys
from typing import Annotated

from pydantic import BaseModel, Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from speed_ramp_mcp import speed_ramp as sr

setup_logging()
mcp = FastMCP("speed-ramp-mcp")

Speed = Annotated[float, Field(ge=0.05, le=16, description="0.5 is half speed, 2 is double")]
Smooth = Annotated[bool, Field(description="Slow motion only: motion-interpolate frames (slower to render)")]


class Segment(BaseModel):
    start: float = Field(ge=0, description="Seconds in the source")
    end: float = Field(gt=0, description="Seconds in the source")
    speed: Speed = 1.0
    smooth: Smooth = True


@mcp.tool()
def change_speed(
    input_path: Annotated[str, Field(description="Source video")],
    speed: Speed = 1.0,
    smooth: Smooth = True,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_speed.<ext>")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Speed up or slow down a whole video; audio pitch is kept."""
    return _run(sr.change_speed, input_path, speed=speed, smooth=smooth, output_path=output_path, lossless=lossless)


@mcp.tool()
def speed_ramp(
    input_path: Annotated[str, Field(description="Source video")],
    segments: Annotated[
        list[Segment],
        Field(min_length=1, description="Time ranges in order, not overlapping; only these ranges are kept"),
    ],
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_ramp.<ext>")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Give each time range its own speed and join them, e.g. normal, slow-mo hit, fast exit."""
    prev_end = 0.0
    for i, s in enumerate(segments):
        if s.end <= s.start:
            raise ToolError(f"segments[{i}]: end must be after start")
        if s.start < prev_end:
            raise ToolError(f"segments[{i}] overlaps the previous one; list ranges in time order")
        prev_end = s.end
    return _run(
        sr.speed_ramp, input_path, [s.model_dump() for s in segments], output_path=output_path, lossless=lossless
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
