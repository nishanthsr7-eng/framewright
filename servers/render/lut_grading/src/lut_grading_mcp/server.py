import os
import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from lut_grading_mcp import grading

setup_logging()
mcp = FastMCP("lut-grading-mcp")

BUILTIN = ", ".join(f"{k} ({v})" for k, v in grading.BUILTIN_LUTS.items())
STYLE_LUTS = {"general": "cinematic_teal_orange", "anime": "anime_vibrant"}


@mcp.tool(
    description=f"Colour-grade a video with a 3D LUT. Built-in LUTs: {BUILTIN}. A path to any .cube file also works."
)
def apply_lut(
    input_path: Annotated[str, Field(description="Source video")],
    lut: Annotated[
        str | None, Field(description="Built-in LUT name, or a path to a .cube file; default comes from style")
    ] = None,
    style: Annotated[
        Literal["anime", "general"], Field(description="Footage type; picks the default LUT when lut is empty")
    ] = "general",
    intensity: Annotated[float, Field(ge=0, le=1, description="Blend with the original; 1 is the full LUT")] = 1.0,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_graded.<ext>")] = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    lut = lut or STYLE_LUTS[style]
    if lut not in grading.BUILTIN_LUTS and not (lut.lower().endswith(".cube") and os.path.isfile(lut)):
        raise ToolError(
            f"Unknown LUT '{lut}'. Use one of: {', '.join(grading.BUILTIN_LUTS)}, or an existing .cube file path."
        )
    return _run(grading.apply_lut, input_path, lut, intensity=intensity, output_path=output_path, lossless=lossless)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
