# Timeline Project

Build a simple edit as a JSON project (clips in order, overlays on top) and render it to one video. A lightweight alternative to building the timeline in DaVinci Resolve.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `create_project` | `project_path`, `width`, `height`, `fps` | empty project file |
| `add_clip` | `project_path`, `file`, `start`, `end`, `transition_in` | updated project |
| `remove_clip` | `project_path`, `index` | updated project |
| `add_overlay` | `project_path`, `file`, `x`, `y`, `width`, `height`, `opacity`, `start_time`, `end_time` | updated project |
| `remove_overlay` | `project_path`, `index` | updated project |
| `get_project` | `project_path` | full project + duration |
| `render_project` | `project_path`, `output_path` | final video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/timeline_project`
- Run: `uv run --directory servers/render/timeline_project timeline-project-mcp`

## Example call

```json
{
  "tool": "add_clip",
  "arguments": {
    "project_path": "output/edit.json",
    "file": "input/a.mp4",
    "start": 1.5,
    "end": 4.0,
    "transition_in": "fade"
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.
