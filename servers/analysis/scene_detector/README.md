# Scene Detector

Find shot changes in a video, and optionally split it into one file per shot.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `detect_scenes` | `video_path`, `threshold`=27, `min_scene_len`=15 frames | list of scene start/end times |
| `split_scenes` | `video_path`, `output_folder`, `threshold`, `min_scene_len` | one clip per scene |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- PySceneDetect, ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/analysis/scene_detector`
- Run: `uv run --directory servers/analysis/scene_detector scene-detector-mcp`

## Example call

```json
{
  "tool": "detect_scenes",
  "arguments": {
    "video_path": "input/episode.mp4",
    "threshold": 27
  }
}
```

## Anime vs general footage

Anime has flat colors and held frames: if cuts are missed, lower `threshold` (around 20). For live action the default is fine.
