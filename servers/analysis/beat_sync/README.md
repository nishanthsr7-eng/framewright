# Beat Sync

Auto-cut a list of clips to a track's beats (a beat-synced edit). Beat times alone come from audio-analyzer `detect_beats`.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `generate_beat_synced_video` | `clip_paths`, `music_path`, `beats_per_cut`=1, `max_duration` | `output_path` of the cut video with the music |
| `build_edit_plan` | `clip_paths`, `music_path`, `beats_per_cut`=2, `max_duration`, `project_name` | `output_path` of an edit plan JSON ([docs/edit-plan.md](../../../docs/edit-plan.md)) with cuts on the beat |
| `validate_plan` | `plan_path`, `base_dir`, `beat_tolerance_frames`=1, `require_beats`=true | `valid`, `errors`, `warnings`, `timeline_duration` |
| `auto_amv_plan` | `clip_paths`, `music_path`, `end_time`, `style`=anime\|general, `pace`=hype\|steady\|chill, `fps`=24, `title` | `output_path`, `clip_count`, `flashes`, `sections`, `validation` |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

`auto_amv_plan` does the whole AMV draft in one call: beats, downbeats and energy sections (librosa), shot cuts (ffmpeg `scene` filter) and per-shot motion. High-motion shots go to drop/chorus, calm ones to intro/outro. Pace `hype` cuts every 2 beats in verses and every beat in drop/chorus. Clips starting on a drop/chorus downbeat get `transition_in: Flash White` + `effects: ["Screen Shake"]`. The plan is validated before returning; render it with timeline-project `render_plan` or build it in Resolve.

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
