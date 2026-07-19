# Framewright

AI-assisted video editing over the **Model Context Protocol (MCP)**.

Framewright is a set of small Python MCP servers that analyze and prepare media: beats, scenes, transcripts, subject cutouts, effects, grading, export. Any LLM (ChatGPT, Claude, Gemini, or a local model) reads their results and writes a **DaVinci Resolve script** that builds the timeline. You keep full control of the final edit in Resolve.

```
media → analysis servers → edit plan JSON → any LLM writes a Resolve script → Resolve builds the timeline
```

Works on both **anime** and **live-action** footage: model-based tools take `style="anime" | "general"`.

---

## What it can do

| Area | Highlights |
|---|---|
| Analysis | Beats, downbeats, song sections, impacts, local speech-to-text with word timestamps, shot detection, audio-based highlight picking |
| Assets | Frame extraction, Real-ESRGAN upscaling, subject cutouts (ISNet for anime, U2-Net for general), chroma key, animated titles, karaoke captions |
| Render | Editing effects and xfade transitions, 7 cinematic LUTs, color matching, film-look overlays, speed ramps, stabilization, Ken Burns, compositing, loudness/ducking, platform export presets |
| Resolve | 90 Fusion templates (titles, effects, transitions, generators) and 20 Lua scripts; all work in the free edition |

Full server list with every tool: [docs/README.md](docs/README.md).

---

## Quick start

1. Install `ffmpeg` and [`uv`](https://docs.astral.sh/uv/).
2. Download models: `python scripts/fetch_models.py`
3. Install a server: `uv sync --directory servers/<group>/<name>` (or all of them, see [docs/setup.md](docs/setup.md))
4. Copy `.mcp.json.example` to `.mcp.json` and point your MCP client at it.
5. Ask for an edit. The full flow is in [docs/workflow.md](docs/workflow.md).

---

## Layout

```
servers/analysis/   audio_analyzer, scene_detector, beat_sync, highlight_reel
servers/assets/     frame_extractor, subject_extractor, chroma_key, text_overlay
servers/render/     effects, lut_grading, color_match, compositor, overlay_fx, speed_ramp,
                    stabilization, ken_burns, audio_mastering, export_presets, timeline_project
resolve/            Lua scripts, Fusion templates, bridge/ (helpers for generated scripts)
prompts/            Prompt templates for the LLM step
examples/           Example edit plans
scripts/            Setup and model download
docs/               Documentation
models/             Model weights (downloaded, not in git)
```

---

## Docs

- [Setup](docs/setup.md): install, models, MCP client config
- [Workflow](docs/workflow.md): from raw clips to a Resolve timeline
- [Architecture](docs/architecture.md): how the pieces fit
- [Edit plan](docs/edit-plan.md): the JSON format the LLM works from
- [DaVinci Resolve](docs/resolve.md): templates, scripts, install
- [Servers](docs/README.md): every server and tool
- [Third-party](docs/third-party.md): credits and related projects

---

## License

MIT, see [LICENSE](LICENSE). Vendored code, models and fonts keep their own licenses; see [docs/third-party.md](docs/third-party.md).
