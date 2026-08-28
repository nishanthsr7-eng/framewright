import logging
import sys
from typing import Annotated

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from stabilization_mcp import stabilize

setup_logging()
mcp = FastMCP("stabilization-mcp")


@mcp.tool()
def stabilize_video(
    input_path: Annotated[str, Field(description="Shaky source video")],
    smoothing: Annotated[int, Field(ge=1, le=100, description="Frames to average; higher is steadier")] = 10,
    shakiness: Annotated[int, Field(ge=1, le=10, description="How shaky the input is")] = 5,
    zoom: Annotated[float, Field(ge=0, le=100, description="Extra zoom % to hide moving edges")] = 0,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_stabilized.<ext>")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Remove handheld shake with two-pass vidstab. Needs an ffmpeg build with libvidstab."""
    try:
        return stabilize.stabilize_video(
            input_path, smoothing=smoothing, shakiness=shakiness, zoom=zoom, output_path=output_path, lossless=lossless
        )
    except FileNotFoundError as e:
        raise ToolError(f"{e}. Check the path exists.") from e
    except (ValueError, RuntimeError) as e:
        msg = str(e)
        if "vidstab" in msg:
            msg += " Install an ffmpeg build with libvidstab (see docs/setup.md)."
        raise ToolError(msg) from e
    except Exception as e:
        logging.exception("Tool failed")
        raise ToolError(f"{type(e).__name__}: {e}") from e


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
