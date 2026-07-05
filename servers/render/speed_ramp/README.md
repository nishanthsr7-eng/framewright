# Speed Ramp

Change playback speed for a whole clip, or per time range (speed ramp), with optional frame interpolation for slow motion.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `change_speed` | `input_path`, `speed`=1.0, `smooth`=True | retimed video |
| `speed_ramp` | `input_path`, `segments` [{`start`, `end`, `speed`, `smooth`}] | ramped video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/speed_ramp`
- Run: `uv run --directory servers/render/speed_ramp speed-ramp-mcp`

## Example call

```json
{
  "tool": "speed_ramp",
  "arguments": {
    "input_path": "input/clip.mp4",
    "segments": [
      {
        "start": 0,
        "end": 2,
        "speed": 1.0
      },
      {
        "start": 2,
        "end": 3,
        "speed": 0.25
      },
      {
        "start": 3,
        "end": 5,
        "speed": 2.0
      }
    ]
  }
}
```

## Anime vs general footage

Interpolation (`smooth`) works well on live action; on anime it can smear line art, so try `smooth=false`.
