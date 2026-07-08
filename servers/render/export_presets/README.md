# Export Presets

Re-encode a video to a social platform's resolution, bitrate and frame rate, handling aspect-ratio changes.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `list_platform_presets` | - | youtube, youtube_shorts, tiktok, instagram_reels, instagram_post, instagram_story, twitter, facebook |
| `export_for_platform` | `video_path`, `platform`, `fit_mode` crop/pad | exported video |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/export_presets`
- Run: `uv run --directory servers/render/export_presets export-presets-mcp`

## Example call

```json
{
  "tool": "export_for_platform",
  "arguments": {
    "video_path": "output/edit.mp4",
    "platform": "tiktok",
    "fit_mode": "crop"
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.
