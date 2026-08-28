# Audio Analyzer

Analyze a soundtrack or a video's audio: beats, downbeats, song sections, impacts, energy over time and local speech-to-text with word timestamps. The output gives the LLM timing anchors for cuts.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `get_audio_info` | `audio_path` | duration, sample rate, RMS loudness |
| `detect_beats` | `audio_path`, `start_time`, `duration` | BPM + beat times |
| `detect_downbeats` | `audio_path`, `beats_per_bar`=4 | first beat of each bar |
| `detect_sections` | `audio_path`, `n_sections` | segments labelled intro/build/drop/chorus/verse (heuristic) |
| `detect_impacts` | `audio_path`, `sensitivity`=1.0 | hit/transient times with strength |
| `analyze_audio_features` | `audio_path`, `window`=1.0 | per-window RMS, spectral centroid, zero-crossing rate |
| `transcribe_audio` | `audio_path`, `model_size`=base, `language`, `word_timestamps`=True | text segments with word timings |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- librosa, faster-whisper (downloads its model on first use), ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/analysis/audio_analyzer`
- Run: `uv run --directory servers/analysis/audio_analyzer audio-analyzer-mcp`

## Example call

```json
{
  "tool": "detect_downbeats",
  "arguments": {
    "audio_path": "input/song.mp3",
    "beats_per_bar": 4
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage. `transcribe_audio` output feeds `add_karaoke_captions` in text_overlay directly.
