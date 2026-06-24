# Chroma Key

Key out a green or blue screen and either keep the alpha or composite onto a new background.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `remove_background` | `input_path`, `color`=0x00FF00, `similarity`=0.18, `blend`=0.05 | transparent `.webm` |
| `replace_background` | `foreground_path`, `background_path`, `color`, `similarity`, `blend` | composited video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/assets/chroma_key`
- Run: `uv run --directory servers/assets/chroma_key chroma-key-mcp`

## Example call

```json
{
  "tool": "replace_background",
  "arguments": {
    "foreground_path": "input/greenscreen.mp4",
    "background_path": "input/city.jpg"
  }
}
```

## Anime vs general footage

For footage without a screen, use subject_extractor instead (model-based).
