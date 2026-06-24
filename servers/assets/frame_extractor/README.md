# Frame Extractor

General ffmpeg utilities: video info, trim, concat, picture-in-picture, scale, frame extraction, and Real-ESRGAN upscaling of frames.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `get_video_info` | `video_path` | duration, fps, codec, size |
| `find_video_path` | `root_path`, `video_name` | full path of a matching file |
| `clip_video` | `video_path`, `start`, `end` or `duration` | trimmed clip |
| `concat_videos` | `input_files`, `fast`=True | joined video |
| `overlay_video` | `background_video`, `overlay_video`, `position` 1-9, `dx`, `dy` | picture-in-picture video |
| `scale_video` | `video_path`, `width`, `height` (-2 keeps aspect) | resized video |
| `extract_frames_from_video` | `video_path`, `fps` (0 = all), `format` 0 png/1 jpg/2 webp, `total_frames` | folder of frames |
| `enhance_frames` | `input_folder`, `model`, `scale`=4, `in_place` | folder of upscaled frames |
| `play_video` | `video_path`, `speed`, `loop` | opens ffplay (local preview) |

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
    "fps": 2,
    "format": 0
  }
}
```

## Anime vs general footage

`enhance_frames`: use `model="realesrgan-x4plus-anime"` for anime and `realesrgan-x4plus` (default) for live action.

---

Vendored from [video-creator/ffmpeg-mcp](https://github.com/video-creator/ffmpeg-mcp) (MIT, see [LICENSE](LICENSE)).
