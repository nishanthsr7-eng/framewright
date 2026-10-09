import sys
from typing import Annotated

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from scene_detector_mcp import detector

setup_logging()
mcp = FastMCP("scene-detector-mcp")

VideoPath = Annotated[str, Field(description="Source video file")]
Threshold = Annotated[float, Field(gt=0, le=100, description="Cut sensitivity; lower finds more cuts")]
MinLen = Annotated[int, Field(ge=1, description="Shortest scene in frames")]


@mcp.tool()
def detect_scenes(video_path: VideoPath, threshold: Threshold = 27.0, min_scene_len: MinLen = 15) -> dict:
    """Find shot changes. Returns each scene's index, start, end and duration in seconds."""
    return _run(detector.detect_scenes, video_path, threshold=threshold, min_scene_len=min_scene_len)


@mcp.tool()
def split_scenes(
    video_path: VideoPath,
    output_folder: Annotated[str | None, Field(description="Default: output/<video>_scenes/")] = None,
    threshold: Threshold = 27.0,
    min_scene_len: MinLen = 15,
) -> dict:
    """Detect shot changes and write each scene to its own video file."""
    return _run(
        detector.split_scenes, video_path, output_folder=output_folder, threshold=threshold, min_scene_len=min_scene_len
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
