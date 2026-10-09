import sys
from typing import Annotated

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from color_match_mcp import color_match

setup_logging()
mcp = FastMCP("color-match-mcp")


@mcp.tool()
def match_color(
    reference_path: Annotated[str, Field(description="Video whose look you want")],
    target_path: Annotated[str, Field(description="Video to adjust")],
    output_path: Annotated[
        str | None, Field(description="Default: output/<target>/<target>_color_matched.<ext>")
    ] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
    samples: Annotated[int, Field(ge=1, le=50, description="Frames sampled from each video")] = 5,
    strength: Annotated[float, Field(ge=0, le=1, description="1 matches fully; 0.5 is a gentler match")] = 1.0,
) -> dict:
    """Match a clip's brightness, contrast and colour cast to a reference clip so shots cut together."""
    return _run(
        color_match.match_color,
        reference_path,
        target_path,
        output_path=output_path,
        lossless=lossless,
        samples=samples,
        strength=strength,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
