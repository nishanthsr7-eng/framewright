import logging
import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from ken_burns_mcp import ken_burns

setup_logging()
mcp = FastMCP("ken-burns-mcp")

Zoom = Annotated[float, Field(ge=1.0, le=4.0, description="Zoom factor (1 = full frame)")]


@mcp.tool()
def create_ken_burns(
    image_path: Annotated[str, Field(description="Still image")],
    duration: Annotated[float, Field(gt=0, le=120, description="Clip length in seconds")] = 5.0,
    zoom_start: Zoom = 1.0,
    zoom_end: Zoom = 1.3,
    pan: Annotated[
        Literal["center", "left_to_right", "right_to_left", "top_to_bottom", "bottom_to_top"],
        Field(description="Pan direction"),
    ] = "center",
    width: Annotated[int, Field(ge=16, le=7680, description="Output width")] = 1920,
    height: Annotated[int, Field(ge=16, le=4320, description="Output height")] = 1080,
    fps: Annotated[int, Field(ge=1, le=120, description="Output frame rate")] = 30,
    output_path: Annotated[str | None, Field(description="Default: output/<image>/<image>_ken_burns.mp4")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Turn a still image into a video with a slow zoom and pan. zoom_end below zoom_start zooms out."""
    try:
        return ken_burns.create_ken_burns(
            image_path,
            duration=duration,
            zoom_start=zoom_start,
            zoom_end=zoom_end,
            pan=pan,
            width=width,
            height=height,
            fps=fps,
            output_path=output_path,
            lossless=lossless,
        )
    except FileNotFoundError as e:
        raise ToolError(f"{e}. Check the path exists.") from e
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e)) from e
    except Exception as e:
        logging.exception("Tool failed")
        raise ToolError(f"{type(e).__name__}: {e}") from e


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
