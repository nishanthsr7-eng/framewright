import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP

from overlay_fx_mcp import effects

setup_logging()
mcp = FastMCP("overlay-fx-mcp")

InputPath = Annotated[str, Field(description="Source video")]
OutputPath = Annotated[str | None, Field(description="Default: output/<video>/<video>_<effect>.<ext>")]


@mcp.tool()
def add_film_grain(
    input_path: InputPath,
    intensity: Annotated[int, Field(ge=0, le=100, description="Grain amount")] = 20,
    output_path: OutputPath = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Add film grain across the whole video."""
    return _run(effects.add_film_grain, input_path, intensity=intensity, output_path=output_path, lossless=lossless)


@mcp.tool()
def add_vignette(
    input_path: InputPath,
    intensity: Annotated[float, Field(ge=0, le=1, description="Darker, wider edges as it rises")] = 0.5,
    output_path: OutputPath = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Darken the frame edges to pull focus to the centre."""
    return _run(effects.add_vignette, input_path, intensity=intensity, output_path=output_path, lossless=lossless)


@mcp.tool()
def add_light_leak(
    input_path: InputPath,
    style: Annotated[Literal["warm", "golden", "cool", "white"], Field(description="Leak colour")] = "warm",
    intensity: Annotated[float, Field(ge=0, le=1, description="Screen-blend strength")] = 0.5,
    pan: Annotated[
        Literal["left_to_right", "right_to_left", "static"], Field(description="How the leak moves")
    ] = "left_to_right",
    output_path: OutputPath = None,
    lossless: Annotated[
        bool, Field(description="Lossless H.264 intermediate for chaining tools; re-encode once at the end")
    ] = False,
) -> dict:
    """Sweep a film light leak across the video. For a colour split, use effects apply_effect rgb_split."""
    return _run(
        effects.add_light_leak,
        input_path,
        style=style,
        intensity=intensity,
        pan=pan,
        output_path=output_path,
        lossless=lossless,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
