# Compositor

Stack image, video and alpha layers over a base video with position, size, opacity and time range per layer.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `compose_layers` | `base_video`, `layers` (bottom to top: `file`, `x`, `y`, `width`, `height`, `opacity`, `start_time`, `end_time`, `audio`) | composited video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/compositor`
- Run: `uv run --directory servers/render/compositor compositor-mcp`

## Example call

```json
{
  "tool": "compose_layers",
  "arguments": {
    "base_video": "output/bg.mp4",
    "layers": [
      {
        "file": "output/hero.webm",
        "x": "(W-w)/2",
        "y": "H-h-40",
        "start_time": 0,
        "end_time": 3
      }
    ]
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. `x`/`y` accept ffmpeg expressions (`W`,`H` = base size, `w`,`h` = layer size).
