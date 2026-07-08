# Ken Burns

Turn a still image into a video clip with slow zoom and pan.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `create_ken_burns` | `image_path`, `duration`=5, `zoom_start`=1.0, `zoom_end`=1.3, `pan` (center, left_to_right, right_to_left, top_to_bottom, bottom_to_top), `width`, `height`, `fps` | video clip |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/ken_burns`
- Run: `uv run --directory servers/render/ken_burns ken-burns-mcp`

## Example call

```json
{
  "tool": "create_ken_burns",
  "arguments": {
    "image_path": "input/poster.jpg",
    "duration": 4,
    "pan": "left_to_right"
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. Good for anime key art and stills.
