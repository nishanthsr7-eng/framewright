import os
import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from export_presets_mcp import exporter

setup_logging()
mcp = FastMCP("export-presets-mcp")

Platform = Literal[tuple(exporter.PRESETS)]
SPECS = "; ".join(f"{k} {v['width']}x{v['height']}" for k, v in exporter.PRESETS.items())


@mcp.tool(description=f"Re-encode a video to a platform's size, bitrate and frame rate. Presets: {SPECS}.")
def export_for_platform(
    video_path: Annotated[str, Field(description="Finished edit")],
    platform: Annotated[Platform, Field(description="Target platform preset")],
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_<platform>.<ext>")] = None,
    fit_mode: Annotated[Literal["crop", "pad"], Field(description="crop fills the frame; pad keeps everything with bars")] = "crop",
) -> dict:
    return _run(exporter.export_for_platform, video_path, platform, output_path=output_path, fit_mode=fit_mode)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
