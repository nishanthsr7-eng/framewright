import json
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

from beat_sync_mcp import amv, beat_sync, plan

setup_logging()
mcp = FastMCP("beat-sync-mcp")


@mcp.tool()
def generate_beat_synced_video(
    clip_paths: Annotated[
        list[str], Field(min_length=1, description="Video clips to cut between, used in order and looped")
    ],
    music_path: Annotated[str, Field(description="Music file; its beats set the cuts and it becomes the soundtrack")],
    output_path: Annotated[str | None, Field(description="Default: output/<music>/<music>_beat_synced.mp4")] = None,
    beats_per_cut: Annotated[int, Field(ge=1, le=16, description="Cut every N beats (1 = every beat)")] = 1,
    max_duration: Annotated[
        float | None, Field(gt=0, description="Cap output length in seconds; default is the song length")
    ] = None,
) -> dict:
    """Build a montage that cuts between clips on the music's beats. For beat times only, use audio-analyzer detect_beats."""
    return _run(
        beat_sync.generate_beat_synced_video,
        clip_paths,
        music_path,
        output_path=output_path,
        beats_per_cut=beats_per_cut,
        max_duration=max_duration,
    )


@mcp.tool()
def build_edit_plan(
    clip_paths: Annotated[list[str], Field(min_length=1, description="Video clips, used in order and looped")],
    music_path: Annotated[str, Field(description="Music file; its beats set the cut points")],
    output_path: Annotated[str | None, Field(description="Default: output/<music>/edit_plan.json")] = None,
    beats_per_cut: Annotated[int, Field(ge=1, le=16, description="Cut every N beats")] = 2,
    max_duration: Annotated[float | None, Field(gt=0, description="Cap timeline length in seconds")] = None,
    project_name: Annotated[str | None, Field(description="Resolve project/timeline name")] = None,
) -> dict:
    """Draft an edit plan JSON (docs/edit-plan.md) with cuts on the beat. Hand it to an LLM with prompts/resolve-script.md."""
    return _run(
        plan.build_edit_plan,
        clip_paths,
        music_path,
        output_path=output_path,
        beats_per_cut=beats_per_cut,
        max_duration=max_duration,
        project_name=project_name,
    )


@mcp.tool()
def validate_plan(
    plan_path: Annotated[str, Field(description="Edit plan JSON file")],
    base_dir: Annotated[
        str | None, Field(description="Folder relative paths resolve against; default is the repo root")
    ] = None,
    beat_tolerance_frames: Annotated[int, Field(ge=0, le=12, description="How far a cut may be from a beat")] = 1,
    require_beats: Annotated[bool, Field(description="Warn when clips don't start on a beat")] = True,
) -> dict:
    """Check an edit plan before Resolve runs it: files exist, ranges fit the clips, no overlaps, cuts on beats."""
    if not os.path.isfile(plan_path):
        raise ToolError(f"Plan not found: {plan_path}")
    try:
        return plan.validate_plan(
            plan_path, base_dir=base_dir, beat_tolerance_frames=beat_tolerance_frames, require_beats=require_beats
        )
    except json.JSONDecodeError as e:
        raise ToolError(f"Plan is not valid JSON: {e}. Fix the file and retry.") from e


@mcp.tool()
def auto_amv_plan(
    clip_paths: Annotated[list[str], Field(min_length=1, description="Source videos to pull shots from")],
    music_path: Annotated[str, Field(description="Music file; sets beats, sections and the soundtrack")],
    output_path: Annotated[str | None, Field(description="Default: output/<music>/amv_plan.json")] = None,
    end_time: Annotated[
        float | None, Field(gt=0, description="Stop the edit at this music time (seconds); default is the full song")
    ] = None,
    style: Annotated[Literal["anime", "general"], Field(description="Footage style; tunes shot detection")] = "anime",
    pace: Annotated[
        Literal["hype", "steady", "chill"],
        Field(description="hype: 2 beats per cut in verses, 1 in drop/chorus; steady: 2 everywhere; chill: 4 / 2"),
    ] = "hype",
    fps: Annotated[float, Field(gt=0, le=120, description="Timeline frame rate")] = 24.0,
    title: Annotated[str | None, Field(description="Optional title shown on the first drop hit")] = None,
    project_name: Annotated[str | None, Field(description="Resolve project/timeline name")] = None,
) -> dict:
    """Make a full AMV edit plan: detect beats/downbeats/sections and shots, pick high-motion shots for drops,
    cut to the beat, mark drop downbeats with Flash White + Screen Shake, then validate. Render with timeline-project render_plan."""
    for p in [music_path, *clip_paths]:
        if not os.path.isfile(p):
            raise ToolError(f"File not found: {p}. Check the path exists.")
    result = _run(
        amv.auto_amv_plan,
        clip_paths,
        music_path,
        output_path=output_path,
        end_time=end_time,
        style=style,
        pace=pace,
        fps=fps,
        title=title,
        project_name=project_name,
    )
    result["validation"] = plan.validate_plan(result["output_path"])
    return result


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
