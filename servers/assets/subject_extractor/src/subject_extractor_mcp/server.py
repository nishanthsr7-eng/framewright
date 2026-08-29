import logging
import os
import sys
from typing import Annotated, Literal

from pydantic import Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import run_tool, setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

import subject_extractor_mcp.segmenter as segmenter
import subject_extractor_mcp.sequence as sequence

setup_logging()
mcp = FastMCP("subject-extractor-mcp")

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@mcp.tool()
def extract_subject(
    input_folder: Annotated[str, Field(description="Folder of frames, e.g. the output of extract_frames_from_video")],
    style: Annotated[
        Literal["anime", "general", "general_hq"],
        Field(
            description="'anime' for animation, 'general' for live-action, 'general_hq' for slower, sharper live-action edges (BiRefNet)"
        ),
    ] = "general",
    output_folder: Annotated[str | None, Field(description="Defaults to '<input_folder>_subject'")] = None,
    with_background: Annotated[bool, Field(description="Also write the background with the subject cut out")] = False,
    threshold: Annotated[float, Field(ge=0.0, le=1.0, description="0 keeps soft edges; >0 binarizes the mask")] = 0.0,
    temporal_smoothing: Annotated[
        float,
        Field(
            ge=0.0, le=0.9, description="Reduce mask flicker between video frames; 0 = off (use for unrelated stills)"
        ),
    ] = 0.5,
    skip_existing: Annotated[
        bool, Field(description="Skip frames whose output already exists (resume a partial run)")
    ] = True,
) -> dict:
    """Cut the main subject out of every frame in a folder and save transparent RGBA PNGs."""
    if not os.path.isdir(input_folder):
        raise ToolError(f"Input folder does not exist: {input_folder}")

    files = sorted(f for f in os.listdir(input_folder) if os.path.splitext(f)[1].lower() in IMG_EXTS)
    if not files:
        raise ToolError(f"No images found in {input_folder} (expected {', '.join(sorted(IMG_EXTS))})")

    output_folder = output_folder or f"{input_folder.rstrip(os.sep).rstrip('/')}_subject"
    os.makedirs(output_folder, exist_ok=True)
    background_folder = f"{output_folder}_background" if with_background else None
    if background_folder:
        os.makedirs(background_folder, exist_ok=True)

    processed, skipped, failed = 0, 0, []
    prev = None  # (frame, mask) of the last processed frame, for temporal smoothing
    for name in files:
        stem = os.path.splitext(name)[0]
        out_path = os.path.join(output_folder, f"{stem}.png")
        if skip_existing and os.path.exists(out_path):
            skipped += 1
            prev = None
            continue
        bg_path = os.path.join(background_folder, f"{stem}.png") if background_folder else None
        try:
            prev = segmenter.split_subject_and_background(
                os.path.join(input_folder, name),
                out_path,
                bg_path,
                style=style,
                threshold=threshold,
                prev=prev,
                smoothing=temporal_smoothing,
            )
            processed += 1
        except FileNotFoundError as e:
            raise ToolError(str(e)) from e
        except Exception as e:  # keep going; report failures at the end
            logging.exception("Failed on %s", name)
            prev = None
            failed.append({"frame": name, "error": str(e)})

    return {
        "output_folder": output_folder,
        "background_folder": background_folder,
        "style": style,
        "processed": processed,
        "skipped": skipped,
        "failed": failed[:10],
        "failed_count": len(failed),
    }


@mcp.tool()
def frames_to_alpha_video(
    input_folder: Annotated[str, Field(description="Folder of RGBA PNGs, e.g. the output of extract_subject")],
    fps: Annotated[float, Field(gt=0, le=120, description="Frame rate; match the source video")] = 24.0,
    output_path: Annotated[str | None, Field(description="A .webm path. Default: '<input_folder>.webm'")] = None,
    lossless: Annotated[bool, Field(description="Lossless VP9; much larger files")] = False,
) -> dict:
    """Turn a PNG sequence with transparency into a VP9 webm that keeps the alpha channel (for Resolve or compositor)."""
    return run_tool(sequence.frames_to_alpha_video, input_folder, fps=fps, output_path=output_path, lossless=lossless)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
