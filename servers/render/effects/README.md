# Effects

Apply editing-style effects (zoom punch, shake, RGB split, flash, glow) and xfade transitions between two clips.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `apply_effect` | `video_path`, `effect`, `intensity`=1.0, `start_time`, `duration` | processed video |
| `apply_transition` | `video_a`, `video_b`, `transition`=fade, `duration`=0.5 | A, transition, then B |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/effects`
- Run: `uv run --directory servers/render/effects effects-mcp`

## Example call

```json
{
  "tool": "apply_effect",
  "arguments": {
    "video_path": "input/clip.mp4",
    "effect": "zoom_punch",
    "start_time": 2.0,
    "duration": 0.4
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.
