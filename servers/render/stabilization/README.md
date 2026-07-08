# Stabilization

Remove handheld shake with ffmpeg's two-pass vidstab.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `stabilize_video` | `input_path`, `smoothing`=10, `shakiness`=5, `zoom`=0 | stabilized video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg built with libvidstab, on PATH
- Install: `uv sync --directory servers/render/stabilization`
- Run: `uv run --directory servers/render/stabilization stabilization-mcp`

## Example call

```json
{
  "tool": "stabilize_video",
  "arguments": {
    "input_path": "input/handheld.mp4",
    "smoothing": 15
  }
}
```

## Anime vs general footage

Meant for live-action camera footage. Anime rarely needs it.
