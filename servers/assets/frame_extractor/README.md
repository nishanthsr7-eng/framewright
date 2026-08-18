# Frame Extractor

General ffmpeg utilities: video info, trim, concat, scale, frame extraction, and Real-ESRGAN upscaling of frames.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `get_video_info` | `video_path` | duration, fps, codec, size |
| `clip_video` | `video_path`, `start`, `end` or `duration` | trimmed clip |
| `concat_videos` | `input_files`, `fast`=false | joined video |
| `scale_video` | `video_path`, `width`, `height` (-2 keeps aspect) | resized video |
| `extract_frames_from_video` | `video_path`, `every_seconds` (0 = all), `format` png/jpg/webp, `max_frames` | `output_folder`, `frame_count` |
| `enhance_frames` | `input_folder`, `style`, `fast`, `scale`=4, `in_place` | folder of upscaled frames |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH; Real-ESRGAN binary in `models/realesrgan/` for `enhance_frames` (`python scripts/fetch_models.py realesrgan`)
- Install: `uv sync --directory servers/assets/frame_extractor`
- Run: `uv run --directory servers/assets/frame_extractor frame-extractor-mcp`

## Example call

```json
{
  "tool": "extract_frames_from_video",
  "arguments": {
    "video_path": "input/clip.mp4",
    "every_seconds": 2,
    "format": "png"
  }
}
```

Picture-in-picture lives in compositor `compose_layers`.

## Anime vs general footage

`enhance_frames`: `style="anime"` uses `realesrgan-x4plus-anime` (or `realesr-animevideov3` with `fast=true`); `style="general"` (default) uses `realesrgan-x4plus`.

---

Vendored from [video-creator/ffmpeg-mcp](https://github.com/video-creator/ffmpeg-mcp) (MIT, see [LICENSE](LICENSE)).
