# Color Match

Match one clip's brightness, contrast and tint to a reference clip.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `match_color` | `reference_path`, `target_path`, `strength`=1.0 | color-matched target |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- numpy, Pillow, ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/color_match`
- Run: `uv run --directory servers/render/color_match color-match-mcp`

## Example call

```json
{
  "tool": "match_color",
  "arguments": {
    "reference_path": "input/a.mp4",
    "target_path": "input/b.mp4",
    "strength": 0.8
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. Lower `strength` on anime to avoid shifting flat color fills too far.
