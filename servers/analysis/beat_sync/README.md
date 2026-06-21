# Beat Sync

Detect a track's beats and auto-cut a list of clips to them (a beat-synced edit).

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `detect_beats` | `music_path` | BPM + beat times |
| `generate_beat_synced_video` | `clip_paths`, `music_path`, `beats_per_cut`=1, `max_duration` | `output_path` of the cut video with the music |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- librosa, ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/analysis/beat_sync`
- Run: `uv run --directory servers/analysis/beat_sync beat-sync-mcp`

## Example call

```json
{
  "tool": "generate_beat_synced_video",
  "arguments": {
    "clip_paths": [
      "input/a.mp4",
      "input/b.mp4"
    ],
    "music_path": "input/song.mp3",
    "beats_per_cut": 2
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.
