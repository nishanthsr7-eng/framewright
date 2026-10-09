# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-10

First tagged release.

### Servers
- 19 MCP servers in three groups: analysis (audio, scenes, beat sync, highlights), assets (frames, subject cut-out, chroma key, text overlays) and render (effects, LUTs, color match, compositing, overlays, speed ramps, stabilization, Ken Burns, audio mastering, export presets, timeline rendering).
- Shared `framewright_core` package: ffmpeg/ffprobe helpers with timeouts, output paths, tool error handling.
- `anime` and `general` style presets, with GPU selection for model-based tools.
- Lossless (qp 0) intermediate option on render servers, chroma_key `replace_background`, ken_burns and text_overlay, so chained tools don't stack re-encode loss.
- `frames_to_alpha_video` tool (subject_extractor): PNG sequence to VP9 webm with alpha.
- Vendored frame_extractor from video-creator/ffmpeg-mcp (MIT): English comments, `logging` instead of `print`, `ToolError` on failure.

### Edit plans and Resolve
- Edit plans: `build_edit_plan`, `auto_amv_plan`, `validate_plan` and `render_plan`.
- `prepare_resolve` tool (timeline_project): bakes an edit plan's cuts (speed, flash, shake, 9:16 crop), titles (alpha overlays) and music so `framewright_build_plan` rebuilds the `render_plan` MP4 frame for frame in Resolve. `render_plan` and `prepare_resolve` share the cut, flash, shake and title code, so both produce the same frames.
- Resolve bridge and `framewright_build_plan.lua`, which builds any plan in Resolve Free. It sets size and frame rate on the new timeline (works in projects that already have timelines), stops on a frame-rate mismatch and sets straight alpha on title overlays.
- 90 Fusion templates and 21 Lua scripts, grouped into menu folders: Edit → Framewright / Markers / Clips, Utility → Export / Timeline / Media Pool.
- Beat-synced cuts are snapped to absolute frames and refined to onsets, so they no longer drift off the beat.
- The Resolve script step targets capable hosted API models; small local models are not supported.

### Evaluation and testing
- Evaluation suite on synthetic, license-free fixtures: beat-sync cut accuracy (0/114 cuts off the beat), beat F-measure, scene cuts (including a harder set with dissolves and near-identical shots), transcription WER (with real-speech support via `--real`) and segmentation IoU.
- `evals/eval_agent.py`: end-to-end LLM eval (plan validity, Lua parse, fake-Resolve build, cuts on beats).
- `scripts/benchmark.py` and a CPU vs GPU performance table.
- Unit and ffmpeg integration tests; CI for lint, format, lockfile, tests and evals; pre-commit hooks.

### Setup
- One-command setup scripts for Windows and Linux/macOS.
- One workspace lockfile; all servers build with hatchling.
- CPU-only `Dockerfile` that runs the smoke test.
- PyAV pinned below 18 so Whisper transcription works on fresh installs.

### Docs
- README written around the editor workflow, with results and performance.
- Design decision records (`docs/decisions/`) and a beat-sync accuracy case study.
- F1 worked example (`demos/f1`): five versions from a first beat plan to a 60 fps looping edit, plus an export of the final version to a Resolve timeline. Scripts and plans only; media stays out of git.
- `CONTRIBUTING.md`, `SECURITY.md`, `CREDITS.md`, `.gitattributes`.
- Licensing: font licenses, third-party notices, pinned model checksums.

[0.1.0]: https://github.com/nishanthsr7-eng/Video_Editor-MCP/releases/tag/v0.1.0
