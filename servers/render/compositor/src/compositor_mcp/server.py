import logging
import sys
from typing import Annotated

from pydantic import BaseModel, Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from compositor_mcp import compositor

setup_logging()
mcp = FastMCP("compositor-mcp")


class Layer(BaseModel):
    file: str = Field(description="Image (static) or video; alpha is respected (e.g. overlay.webm, subject PNGs)")
    x: int | str = Field(0, description="Pixels or ffmpeg expression with W,H (base) and w,h (layer), e.g. '(W-w)/2'")
    y: int | str = Field(0, description="Pixels or expression, e.g. 'H-h-40'")
    width: int | None = Field(None, description="Scale to this width; -1 keeps aspect with height")
    height: int | None = Field(None, description="Scale to this height; -1 keeps aspect with width")
    opacity: float = Field(1.0, ge=0, le=1)
    start_time: float | None = Field(None, ge=0, description="Visible from (seconds on the base timeline)")
    end_time: float | None = Field(None, gt=0, description="Visible until (seconds)")
    audio: bool = Field(False, description="Video layers only: mix this layer's audio in")


@mcp.tool()
def compose_layers(
    base_video: Annotated[str, Field(description="Background video; sets size, fps and length")],
    layers: Annotated[list[Layer], Field(min_length=1, description="Layers bottom to top")],
    output_path: Annotated[str | None, Field(description="Default: output/<base>/<base>_composite.<ext>")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Stack images and videos over a base video with position, size, opacity and timing.
    Use for picture-in-picture, cut-out subjects, and title or caption overlays."""
    for i, layer in enumerate(layers):
        if layer.start_time is not None and layer.end_time is not None and layer.end_time <= layer.start_time:
            raise ToolError(f"layers[{i}]: end_time must be after start_time")
    try:
        return compositor.compose_layers(
            base_video=base_video,
            layers=[l.model_dump(exclude_none=True) for l in layers],
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
