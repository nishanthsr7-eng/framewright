import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")  # pyright: ignore[reportAttributeAccessIssue]


from framewright_core import run_tool as _run
from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from text_overlay_mcp import overlay, renderer

setup_logging()
mcp = FastMCP("text-overlay-mcp")

FontName = Literal[tuple(renderer.list_fonts())]  # bundled bold sans fonts
Style = Annotated[Literal["anime", "general"], Field(description="Footage type; fills any look options left empty")]

# Defaults per footage style; only used for params the caller leaves as None.
TEXT_STYLES = {
    "general": {"font": "anton", "outline_width": 0, "shadow": False},
    "anime": {"font": "bangers", "outline_width": 8, "shadow": True},
}
CAPTION_STYLES = {
    "general": {"font": "anton", "outline_width": 6, "shadow": True, "highlight_color": "#FFD700"},
    "anime": {"font": "bangers", "outline_width": 8, "shadow": True, "highlight_color": "#FF4FA3"},
}


def _fill(preset: dict, **given) -> dict:
    return {k: preset[k] if v is None else v for k, v in given.items()}


Hex = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Colour as #RRGGBB")]
Position = Annotated[Literal["top", "center", "bottom"], Field(description="Vertical placement")]
Fps = Annotated[float | None, Field(gt=0, le=60, description="Overlay frame rate; default is the source rate, max 30")]
Lossless = Annotated[
    bool, Field(description="Lossless H.264 burned-in copy for chaining tools; re-encode once at the end")
]
OutFolder = Annotated[str | None, Field(description="Default: output/<video>_<kind>/")]


@mcp.tool()
def add_text_overlay(
    video_path: Annotated[str, Field(description="Source video")],
    text: Annotated[str, Field(min_length=1, description="Text to show; '\\n' starts a new line")],
    output_folder: OutFolder = None,
    style: Style = "general",
    font: Annotated[FontName | None, Field(description="Bundled font; default from style")] = None,  # pyright: ignore[reportInvalidTypeForm]
    font_size: Annotated[int | None, Field(gt=0, description="Pixels; default is about 9% of video height")] = None,
    color: Annotated[Hex | list[Hex], Field(description="One colour, or two for a top-to-bottom gradient")] = "#FFFFFF",
    outline_color: Hex = "#000000",
    outline_width: Annotated[
        int | None, Field(ge=0, le=40, description="Outline in pixels; 0 for none; default from style")
    ] = None,
    shadow: Annotated[bool | None, Field(description="Add a drop shadow; default from style")] = None,
    position: Position = "center",
    start_time: Annotated[float, Field(ge=0, description="When the text appears, in seconds")] = 0.0,
    duration: Annotated[float | None, Field(gt=0, description="Seconds on screen; default is to the end")] = None,
    animation: Annotated[
        Literal["none", "fade", "word_by_word", "typewriter"], Field(description="How the text appears")
    ] = "word_by_word",
    fps: Fps = None,
    lossless: Lossless = False,
) -> dict:
    """Add bold title text to a video. Writes a transparent overlay.webm and a burned-in copy."""
    if isinstance(color, list) and len(color) not in (1, 2):
        raise ToolError("color takes one hex colour or a list of two for a gradient")
    look = _fill(TEXT_STYLES[style], font=font, outline_width=outline_width, shadow=shadow)
    return _run(
        overlay.create_text_overlay,
        video_path=video_path,
        text=text,
        output_folder=output_folder,
        font_size=font_size,
        color=color,
        outline_color=outline_color,
        **look,
        position=position,
        start_time=start_time,
        duration=duration,
        animation=animation,
        fps=fps,
        lossless=lossless,
    )


@mcp.tool()
def add_karaoke_captions(
    video_path: Annotated[str, Field(description="Source video")],
    segments: Annotated[
        list[dict], Field(min_length=1, description="The 'segments' list from transcribe_audio (word_timestamps=true)")
    ],
    output_folder: OutFolder = None,
    style: Style = "general",
    font: Annotated[FontName | None, Field(description="Bundled font; default from style")] = None,  # pyright: ignore[reportInvalidTypeForm]
    font_size: Annotated[int | None, Field(gt=0, description="Pixels; default is about 5.5% of video height")] = None,
    color: Annotated[Hex, Field(description="Colour of words not yet spoken")] = "#FFFFFF",
    highlight_color: Annotated[Hex | None, Field(description="Colour of spoken words; default from style")] = None,
    outline_color: Hex = "#000000",
    outline_width: Annotated[
        int | None, Field(ge=0, le=40, description="Outline in pixels; default from style")
    ] = None,
    shadow: Annotated[bool | None, Field(description="Add a drop shadow; default from style")] = None,
    position: Position = "bottom",
    max_words_per_line: Annotated[int, Field(ge=1, le=20, description="Words per caption line")] = 6,
    fps: Fps = None,
    lossless: Lossless = False,
) -> dict:
    """Word-by-word highlighted captions from transcribe_audio output. Writes overlay.webm and a burned-in copy."""
    if not any(s.get("words") for s in segments):
        raise ToolError("segments have no 'words'. Run transcribe_audio with word_timestamps=true.")
    look = _fill(
        CAPTION_STYLES[style], font=font, outline_width=outline_width, shadow=shadow, highlight_color=highlight_color
    )
    return _run(
        overlay.create_karaoke_captions,
        video_path=video_path,
        segments=segments,
        output_folder=output_folder,
        font_size=font_size,
        color=color,
        outline_color=outline_color,
        **look,
        position=position,
        max_words_per_line=max_words_per_line,
        fps=fps,
        lossless=lossless,
    )


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
