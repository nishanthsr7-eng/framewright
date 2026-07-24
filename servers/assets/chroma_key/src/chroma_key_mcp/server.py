import os
import sys
from typing import Annotated

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from chroma_key_mcp import chroma

setup_logging()
mcp = FastMCP("chroma-key-mcp")

KeyColor = Annotated[str, Field(pattern=r"^(0x|#)[0-9A-Fa-f]{6}$", description="Screen colour: 0x00FF00 green, 0x0000FF blue")]
Similarity = Annotated[float, Field(ge=0.01, le=1, description="Colour tolerance; higher removes more")]
Blend = Annotated[float, Field(ge=0, le=1, description="Edge softness")]


def _norm(color: str) -> str:
    return "0x" + color[-6:]


@mcp.tool()
def remove_background(
    input_path: Annotated[str, Field(description="Green- or blue-screen video")],
    color: KeyColor = "0x00FF00",
    similarity: Similarity = 0.18,
    blend: Blend = 0.05,
    output_path: Annotated[str | None, Field(description="Output .webm; default: output/<video>/<video>_keyed.webm")] = None,
) -> dict:
    """Key out a solid screen colour. Writes a .webm with alpha, ready to use as an overlay layer."""
    return _run(chroma.remove_background, input_path, color=_norm(color), similarity=similarity,
                blend=blend, output_path=output_path)


@mcp.tool()
def replace_background(
    foreground_path: Annotated[str, Field(description="Green- or blue-screen video; sets size, fps and length")],
    background_path: Annotated[str, Field(description="New background image or video (looped and cropped to fit)")],
    color: KeyColor = "0x00FF00",
    similarity: Similarity = 0.18,
    blend: Blend = 0.05,
    output_path: Annotated[str | None, Field(description="Default: output/<video>/<video>_bg_replaced.<ext>")] = None,
) -> dict:
    """Key out a screen colour and put the subject over a new background in one step."""
    return _run(chroma.replace_background, foreground_path, background_path, color=_norm(color),
                similarity=similarity, blend=blend, output_path=output_path)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
