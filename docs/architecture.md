# Architecture

## Idea

Editing has two halves: **understanding the media** (where are the beats, the cuts, the words, the subject) and **building the timeline**. Framewright gives the first half to small, deterministic tools, and hands the second to DaVinci Resolve. An LLM sits between them and does the one thing it is good at: turning analysis plus a request into a script.

```
              ┌────────────────────── MCP ───────────────────────┐
 media ──►    │ analysis servers   asset servers   render servers │ ──► JSON + files
              └───────────────────────────────────────────────────┘
                                   │
                                   ▼
                        edit plan JSON (docs/edit-plan.md)
                                   │
                                   ▼
                hosted LLM + prompts/resolve-script.md
                                   │
                                   ▼
             Resolve Python script (uses resolve/bridge helpers)
                                   │
                                   ▼
                      DaVinci Resolve builds the timeline
```

There is also a Resolve-free path: render servers and `timeline_project` can produce a finished video with ffmpeg alone.

## Design rules

- **One job per server.** Servers never call each other. The client (LLM) chains them by passing file paths.
- **Plain data out.** Every tool returns a dict: `output_path` plus metadata (times, BPM, segments). Easy to put in an edit plan.
- **Deterministic.** Same input, same output. No hidden model calls except the local models below.
- **Files, not memory.** Results land in `output/`, so any step can be inspected or re-run.
- **Footage style.** Model-based tools take `style="anime" | "general"`.
- **LLM-neutral.** Nothing depends on a specific AI vendor; MCP and plain JSON are the only interfaces.

## Server groups

| Group | Servers | Role |
|---|---|---|
| `servers/analysis/` | audio_analyzer, scene_detector, beat_sync, highlight_reel | Read media, return timings |
| `servers/assets/` | frame_extractor, subject_extractor, chroma_key, text_overlay | Make building blocks: frames, cutouts, keyed clips, title overlays |
| `servers/render/` | effects, lut_grading, color_match, compositor, overlay_fx, speed_ramp, stabilization, ken_burns, audio_mastering, export_presets, timeline_project | Transform or assemble video with ffmpeg |

Per-server tools: [README.md](README.md).

## Inside a server

```
servers/<group>/<name>/
  pyproject.toml          deps + console script (<name>-mcp)
  README.md
  src/<pkg>_mcp/
    server.py             MCP tool definitions (FastMCP, stdio)
    <logic>.py            the actual work
```

- stdout is the MCP channel; logs go to stderr.
- ffmpeg and ffprobe run as subprocesses with an argument list and a timeout (shared helpers in `servers/core`).
- Bad input raises a `ToolError` with a fix hint.
- Each server finds the repo root by walking up to `servers/`, then uses `output/` and `models/`.

## Models

| Model | Runtime | Where |
|---|---|---|
| ISNet anime-seg, U2-Net | ONNX Runtime (CPU) | subject_extractor |
| Real-ESRGAN | ncnn-vulkan binary (GPU) | frame_extractor |
| faster-whisper | CTranslate2 (CPU/GPU) | audio_analyzer |
| librosa DSP | numpy | audio_analyzer, beat_sync, highlight_reel |
| PySceneDetect | OpenCV | scene_detector |

## Resolve side

`resolve/` holds Lua scripts and Fusion templates you install into Resolve, plus `resolve/bridge/`, a helper library that LLM-generated scripts import (connect, import media, build timeline, add markers). Details: [resolve.md](resolve.md).

## Example data flow

```
detect_scenes(source.mp4)                      → [{start, end}, ...]
extract_frames_from_video(scene_03.mp4)        → output/.../frame_0001.png ...
enhance_frames(frames/, model=x4plus-anime)    → 4x upscaled frames
extract_subject(frames/, style="anime")        → transparent PNG cutouts
detect_beats(music.mp3)                        → {tempo_bpm, beat_times}
transcribe_audio(vocals.mp4)                   → {segments: [{text, words}]}
add_text_overlay(clip.mp4, "FINALLY FREE")     → overlay.webm (alpha)
compose_layers(bg.mp4, [cutout, overlay])      → composite.mp4
apply_lut(composite.mp4, "cinematic_teal_orange")
export_for_platform(graded.mp4, "tiktok")
```

## Design decisions

Why it is built this way: [decisions/](decisions/README.md).

- [Lua script instead of live control](decisions/0001-lua-script-not-live-control.md)
- [One process per server](decisions/0002-one-process-per-server.md)
- [File handoff via `output/`](decisions/0003-file-handoff-via-output.md)
- [Lossless qp-0 intermediates](decisions/0004-lossless-intermediates.md)
- Case study: [beat-sync accuracy](case-study-beat-sync.md)
