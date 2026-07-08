# Audio Mastering

Finish the soundtrack: loudness normalization, denoise, and background music with automatic ducking under speech.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `normalize_loudness` | `input_path`, `target_lufs`=-14 | normalized file |
| `reduce_noise` | `input_path`, `amount`=12 | denoised file |
| `add_background_music` | `video_path`, `music_path`, `music_volume_db`=-20, `duck`=True, `loop`=True | video with mixed music |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/render/audio_mastering`
- Run: `uv run --directory servers/render/audio_mastering audio-mastering-mcp`

## Example call

```json
{
  "tool": "add_background_music",
  "arguments": {
    "video_path": "output/edit.mp4",
    "music_path": "input/song.mp3",
    "duck": true
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. -14 LUFS suits YouTube/TikTok.
