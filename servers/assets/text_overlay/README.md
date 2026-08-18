# Text Overlay

Render bold, animated editing-style titles and word-by-word karaoke captions onto a video.

## Tools

| Tool | Key inputs | Output |
|---|---|---|
| `add_text_overlay` | `video_path`, `text`, `font`, `position` top/center/bottom, `start_time`, `duration`, `animation` (none, fade, word_by_word, typewriter, ...) | video with text |
| `add_karaoke_captions` | `video_path`, `segments` (from `transcribe_audio`), `highlight_color`, `max_words_per_line`=6 | video with highlighted captions |

All tools return a dict (usually with `output_path`). Outputs default to `output/` at the repo root.

## Requirements

- Pillow, ffmpeg/ffprobe on PATH
- Install: `uv sync --directory servers/assets/text_overlay`
- Run: `uv run --directory servers/assets/text_overlay text-overlay-mcp`

## Example call

```json
{
  "tool": "add_text_overlay",
  "arguments": {
    "video_path": "input/clip.mp4",
    "text": "IT WAS YOU",
    "animation": "word_by_word",
    "position": "center"
  }
}
```

## Anime vs general footage

Style-neutral: works the same on anime and live-action footage.

## Credits

Bundled fonts (Anton, Bebas Neue, Montserrat, Oswald, Poppins) are from [Google Fonts](https://fonts.google.com) under the SIL Open Font License.
