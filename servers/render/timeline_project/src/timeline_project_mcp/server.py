import logging
import os
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, Field

if sys.platform == "win32":
    sys.stderr.reconfigure(encoding="utf-8")


from framewright_core import setup_logging
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from timeline_project_mcp import plan_render
from timeline_project_mcp import project as proj

setup_logging()
mcp = FastMCP("timeline-project-mcp")

# Same xfade names as effects-mcp.
Transition = Literal[
    "fade",
    "fadeblack",
    "fadewhite",
    "dissolve",
    "pixelize",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "slideup",
    "slidedown",
    "smoothleft",
    "smoothright",
    "smoothup",
    "smoothdown",
    "circlecrop",
    "rectcrop",
    "circleopen",
    "circleclose",
    "vertopen",
    "vertclose",
    "horzopen",
    "horzclose",
    "diagtl",
    "diagtr",
    "diagbl",
    "diagbr",
    "hlslice",
    "hrslice",
    "vuslice",
    "vdslice",
    "hblur",
    "distance",
    "zoomin",
    "hlwind",
    "hrwind",
    "vuwind",
    "vdwind",
    "coverleft",
    "coverright",
    "coverup",
    "coverdown",
    "revealleft",
    "revealright",
    "revealup",
    "revealdown",
    "wipetl",
    "wipetr",
    "wipebl",
    "wipebr",
]


class Clip(BaseModel):
    file: str = Field(description="Video or image")
    start: float = Field(0.0, ge=0, description="In-point in the source, seconds")
    end: float | None = Field(None, gt=0, description="Out-point; default is the whole video, or 5 s for images")
    transition_in: Transition | None = Field(None, description="Transition from the previous clip")
    transition_in_duration: float = Field(0.5, gt=0, le=5)


class Overlay(BaseModel):
    file: str = Field(description="Image or video with alpha (e.g. overlay.webm)")
    x: int = Field(0, description="Left edge in pixels")
    y: int = Field(0, description="Top edge in pixels")
    width: int | None = Field(None, description="Scale width; -1 keeps aspect")
    height: int | None = Field(None, description="Scale height; -1 keeps aspect")
    opacity: float = Field(1.0, ge=0, le=1)
    start_time: float = Field(0.0, ge=0, description="Seconds on the final timeline")
    end_time: float | None = Field(None, gt=0, description="Default: to the end")
    audio: bool = Field(False, description="Mix in this overlay's audio")


@mcp.tool()
def render_timeline(
    clips: Annotated[list[Clip], Field(min_length=1, description="Clips played in order")],
    overlays: Annotated[
        list[Overlay] | None, Field(description="Layers over the whole timeline, bottom to top")
    ] = None,
    width: Annotated[int, Field(ge=16, le=7680, description="Canvas width")] = 1920,
    height: Annotated[int, Field(ge=16, le=4320, description="Canvas height")] = 1080,
    fps: Annotated[float, Field(gt=0, le=120, description="Output frame rate")] = 30,
    output_path: Annotated[str | None, Field(description="Default: output/timeline/timeline_render.mp4")] = None,
    project_path: Annotated[
        str | None, Field(description="Also save the timeline as JSON here; default: output/timeline/timeline.json")
    ] = None,
) -> dict:
    """Render a simple edit without Resolve: clips in order with transitions, then overlays, to one mp4.
    For a full NLE timeline, use the Resolve bridge instead."""
    for i, c in enumerate(clips):
        if c.end is not None and c.end <= c.start:
            raise ToolError(f"clips[{i}]: end must be after start")
    overlays = overlays or []
    for i, o in enumerate(overlays):
        if o.end_time is not None and o.end_time <= o.start_time:
            raise ToolError(f"overlays[{i}]: end_time must be after start_time")
    try:
        if project_path is None:
            out_dir = os.path.dirname(output_path) if output_path else os.path.join(proj._get_output_root(), "timeline")
            os.makedirs(out_dir, exist_ok=True)
            project_path = os.path.join(out_dir, "timeline.json")
        proj.create_project(project_path, width=width, height=height, fps=fps)
        for c in clips:
            proj.add_clip(project_path, **c.model_dump())
        for o in overlays:
            proj.add_overlay(project_path, **o.model_dump())
        result = proj.render_project(project_path, output_path=output_path)
        result["project_path"] = project_path
        return result
    except FileNotFoundError as e:
        raise ToolError(f"{e}. Check the path exists.") from e
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e)) from e
    except Exception as e:
        logging.exception("Tool failed")
        raise ToolError(f"{type(e).__name__}: {e}") from e


@mcp.tool()
def render_plan(
    plan_path: Annotated[str, Field(description="Edit plan JSON (docs/edit-plan.md), e.g. from auto_amv_plan")],
    output_path: Annotated[str | None, Field(description="Default: output/plans/<plan>.mp4")] = None,
    platform: Annotated[
        Literal["none", "tiktok"],
        Field(description="tiktok: center-crop to 1080x1920; titles are drawn after the crop"),
    ] = "none",
    base_dir: Annotated[
        str | None, Field(description="Folder relative plan paths resolve against; default is the repo root")
    ] = None,
    crf: Annotated[int, Field(ge=0, le=40, description="x264 quality; lower is better")] = 18,
) -> dict:
    """Render an edit plan to MP4 without Resolve: frame-exact cuts on track 1, speed, music,
    Flash White / Screen Shake on marked clips, and plan titles. Run validate_plan first."""
    if not os.path.isfile(plan_path):
        raise ToolError(f"Plan not found: {plan_path}. Create one with build_edit_plan or auto_amv_plan.")
    try:
        return plan_render.render_plan(
            plan_path, output_path=output_path, platform=platform, base_dir=base_dir, crf=crf
        )
    except FileNotFoundError as e:
        raise ToolError(f"Missing {e}. Check paths, or pass base_dir.") from e
    except (KeyError, TypeError) as e:
        raise ToolError(f"Plan is missing or has a bad field ({e}). Run validate_plan and fix it.") from e
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e)) from e
    except Exception as e:
        logging.exception("Tool failed")
        raise ToolError(f"{type(e).__name__}: {e}") from e


@mcp.tool()
def prepare_resolve(
    plan_path: Annotated[str, Field(description="Edit plan JSON (docs/edit-plan.md), e.g. from auto_amv_plan")],
    platform: Annotated[
        Literal["none", "tiktok"], Field(description="Use the same value you passed to render_plan")
    ] = "none",
    base_dir: Annotated[
        str | None, Field(description="Folder relative plan paths resolve against; default is the repo root")
    ] = None,
) -> dict:
    """Make the plan land in DaVinci Resolve exactly like render_plan's MP4: bakes each cut (speed, flash,
    shake, crop), titles as alpha overlays and the music, then writes output/framewright_plan.lua.
    Then run Workspace > Scripts > Edit > Framewright > framewright_build_plan in Resolve."""
    if not os.path.isfile(plan_path):
        raise ToolError(f"Plan not found: {plan_path}. Create one with build_edit_plan or auto_amv_plan.")
    try:
        return plan_render.prepare_resolve(plan_path, platform=platform, base_dir=base_dir)
    except FileNotFoundError as e:
        raise ToolError(f"Missing {e}. Check paths, or pass base_dir.") from e
    except (KeyError, TypeError) as e:
        raise ToolError(f"Plan is missing or has a bad field ({e}). Run validate_plan and fix it.") from e
    except (ValueError, RuntimeError) as e:
        raise ToolError(str(e)) from e
    except Exception as e:
        logging.exception("Tool failed")
        raise ToolError(f"{type(e).__name__}: {e}") from e


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
