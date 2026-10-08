# Timeline Project

Render a simple edit in one call: clips in order with transitions, overlays on top, one mp4. The timeline is also saved as JSON. A lightweight alternative to building the timeline in DaVinci Resolve.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `render_timeline` | `clips` [{file, start, end, transition_in}], `overlays` [{file, x, y, width, height, opacity, start_time, end_time}], `width`, `height`, `fps` | `output_path`, `duration`, `project_path` |
| `render_plan` | `plan_path`, `output_path`, `platform`=none\|tiktok, `base_dir`, `crf`=18 | `output_path`, `duration`, `expected_duration`, `cuts`, `flashes`, `titles` |
| `prepare_resolve` | `plan_path`, `platform`=none\|tiktok, `base_dir` | `output_path` (framewright_plan.lua), `media_dir`, `cuts`, `titles`, `width`, `height`, `frames` |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

`render_plan` renders any edit plan (`docs/edit-plan.md`) without Resolve: track-1 clips cut frame-exact at their `at` times (gaps become black), `speed`, music with `gain_db` and a fade-out, a white flash for `transition_in` types containing "Flash" and a shake for `effects` containing "Shake" and `titles` as centered text. `platform="tiktok"` center-crops to 1080x1920 and draws titles after the crop. Other tracks are skipped (reported as `skipped_other_tracks`).

`prepare_resolve` makes the same edit land in DaVinci Resolve frame for frame. The Resolve API can't retime clips or add transitions, so each cut is baked exactly as `render_plan` draws it (speed, flash, shake, 9:16 crop) into `output/resolve/<plan>_<time>/`, titles become transparent ProRes 4444 overlays on V2+ and the music is baked with its gain and fade. It then writes `output/framewright_plan.lua`; run `framewright_build_plan` in Resolve. Pink markers note what was baked into each cut. Use the same `platform` you rendered with.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/timeline_project`
- Run: `uv run --directory servers/render/timeline_project timeline-project-mcp`

## Example call

```json
{
  "tool": "render_timeline",
  "arguments": {
    "clips": [
      {"file": "input/a.mp4", "start": 1.5, "end": 4.0},
      {"file": "input/b.mp4", "end": 3.0, "transition_in": "fade"}
    ],
    "overlays": [{"file": "output/a_text_overlay/overlay.webm"}],
    "width": 1080, "height": 1920
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.
