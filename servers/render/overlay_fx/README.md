# Overlay FX

Add film-look overlays: grain, vignette, chromatic aberration and moving light leaks.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `add_film_grain` | `input_path`, `intensity`=20 | video with grain |
| `add_vignette` | `input_path`, `intensity`=0.5 | video with vignette |
| `add_chromatic_aberration` | `input_path`, `shift`=3 px | video with RGB fringe |
| `add_light_leak` | `input_path`, `style` warm/golden/cool/white, `intensity`=0.5, `pan` left_to_right/right_to_left/static | video with light leak |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/overlay_fx`
- Run: `uv run --directory servers/render/overlay_fx overlay-fx-mcp`

## Example call

```json
{
  "tool": "add_light_leak",
  "arguments": {
    "input_path": "input/clip.mp4",
    "style": "golden",
    "intensity": 0.4
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.
