# Highlight Reel

Score a video's audio (loudness + impacts) and cut the most intense moments into a short reel.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `generate_highlights` | `video_path`, `target_duration`=30, `clip_duration`=3, `min_gap`=2 | `output_path` + chosen time ranges |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- librosa, ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/analysis/highlight_reel`
- Run: `uv run --directory servers/analysis/highlight_reel highlight-reel-mcp`

## Example call

```json
{
  "tool": "generate_highlights",
  "arguments": {
    "video_path": "input/match.mp4",
    "target_duration": 20
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. Picks by audio only, so quiet-but-visual moments can be missed.
