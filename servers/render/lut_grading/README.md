# LUT Grading

Apply built-in cinematic 3D LUT color grades at adjustable strength.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `list_luts` | - | cinematic_teal_orange, warm_vintage, cool_blue, high_contrast_bw, faded_film, moody_green, bleach_bypass |
| `apply_lut` | `input_path`, `lut`, `intensity`=1.0 | graded video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/lut_grading`
- Run: `uv run --directory servers/render/lut_grading lut-grading-mcp`

## Example call

```json
{
  "tool": "apply_lut",
  "arguments": {
    "input_path": "input/clip.mp4",
    "lut": "cinematic_teal_orange",
    "intensity": 0.7
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. Anime usually looks better at `intensity` 0.4-0.7.
