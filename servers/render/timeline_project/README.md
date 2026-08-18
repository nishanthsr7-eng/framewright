# Timeline Project

Render a simple edit in one call: clips in order with transitions, overlays on top, one mp4. The timeline is also saved as JSON. A lightweight alternative to building the timeline in DaVinci Resolve.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `render_timeline` | `clips` [{file, start, end, transition_in}], `overlays` [{file, x, y, width, height, opacity, start_time, end_time}], `width`, `height`, `fps` | `output_path`, `duration`, `project_path` |
| `render_plan` | `plan_path`, `output_path`, `platform`=none\|tiktok, `base_dir`, `crf`=18 | `output_path`, `duration`, `expected_duration`, `cuts`, `flashes`, `titles` |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

`render_plan` renders any edit plan (`docs/edit-plan.md`) without Resolve: track-1 clips cut frame-exact at their `at` times (gaps become black), `speed`, music with `gain_db` and a fade-out, a white flash for `transition_in` types containing "Flash" and a shake for `effects` containing "Shake", and `titles` as centered text. `platform="tiktok"` center-crops to 1080x1920 and draws titles after the crop. Other tracks are skipped (reported as `skipped_other_tracks`).

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
