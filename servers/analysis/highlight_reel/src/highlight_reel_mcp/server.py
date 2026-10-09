import sys
from typing import Annotated

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from highlight_reel_mcp import highlights

setup_logging()
mcp = FastMCP("highlight-reel-mcp")


@mcp.tool()
def generate_highlights(
    video_path: Annotated[str, Field(description="Source video; must have an audio track")],
    target_duration: Annotated[float, Field(gt=0, description="Target reel length in seconds (approximate)")] = 30.0,
    clip_duration: Annotated[float, Field(gt=0, description="Length of each picked clip in seconds")] = 3.0,
    min_gap: Annotated[float, Field(ge=0, description="Minimum seconds between picked clips")] = 2.0,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_highlights.<ext>")] = None,
) -> dict:
    """Pick the loudest, most energetic moments by audio and join them in time order into a highlight reel."""
    return _run(
        highlights.generate_highlights,
        video_path,
        target_duration=target_duration,
        clip_duration=clip_duration,
        min_gap=min_gap,
        output_path=output_path,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
