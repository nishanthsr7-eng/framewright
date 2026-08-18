# Server index

Framewright is a set of small MCP servers. Each one does one job and returns file paths and metadata. An LLM reads the results and writes the DaVinci Resolve script that builds the timeline (see [resolve.md](resolve.md); for Resolve Free, [resolve-free-scripts.md](resolve-free-scripts.md)).

Setup: [setup.md](setup.md). Design: [architecture.md](architecture.md).

## Analysis: understand the footage and music

| Server | Tools | What it does |
|---|---|---|
| [Audio Analyzer](../servers/analysis/audio_analyzer/README.md) | 7 | Analyze a soundtrack or a video's audio: beats, downbeats, song sections, impacts, energy over time, and local speech-to-text with word timestamps. |
| [Beat Sync](../servers/analysis/beat_sync/README.md) | 1 | Auto-cut a list of clips to a track's beats (a beat-synced edit). |
| [Highlight Reel](../servers/analysis/highlight_reel/README.md) | 1 | Score a video's audio (loudness + impacts) and cut the most intense moments into a short reel. |
| [Scene Detector](../servers/analysis/scene_detector/README.md) | 2 | Find shot changes in a video, and optionally split it into one file per shot. |

## Assets: prepare frames, cutouts and text

| Server | Tools | What it does |
|---|---|---|
| [Chroma Key](../servers/assets/chroma_key/README.md) | 2 | Key out a green or blue screen and either keep the alpha or composite onto a new background. |
| [Frame Extractor](../servers/assets/frame_extractor/README.md) | 6 | General ffmpeg utilities: video info, trim, concat, scale, frame extraction, and Real-ESRGAN upscaling of frames. |
| [Subject Extractor](../servers/assets/subject_extractor/README.md) | 1 | Cut the main subject out of every frame in a folder and save transparent PNGs, ready for compositing. |
| [Text Overlay](../servers/assets/text_overlay/README.md) | 2 | Render bold, animated editing-style titles and word-by-word karaoke captions onto a video. |

## Render: effects, grading, audio and export

| Server | Tools | What it does |
|---|---|---|
| [Audio Mastering](../servers/render/audio_mastering/README.md) | 3 | Finish the soundtrack: loudness normalization, denoise, and background music with automatic ducking under speech. |
| [Color Match](../servers/render/color_match/README.md) | 1 | Match one clip's brightness, contrast and tint to a reference clip. |
| [Compositor](../servers/render/compositor/README.md) | 1 | Stack image, video and alpha layers over a base video with position, size, opacity and time range per layer. |
| [Effects](../servers/render/effects/README.md) | 2 | Apply editing-style effects (zoom punch, shake, RGB split, flash, glow) and xfade transitions between two clips. |
| [Export Presets](../servers/render/export_presets/README.md) | 1 | Re-encode a video to a social platform's resolution, bitrate and frame rate, handling aspect-ratio changes. |
| [Ken Burns](../servers/render/ken_burns/README.md) | 1 | Turn a still image into a video clip with slow zoom and pan. |
| [LUT Grading](../servers/render/lut_grading/README.md) | 1 | Apply built-in cinematic 3D LUT color grades at adjustable strength. |
| [Overlay FX](../servers/render/overlay_fx/README.md) | 3 | Add film-look overlays: grain, vignette and moving light leaks. |
| [Speed Ramp](../servers/render/speed_ramp/README.md) | 2 | Change playback speed for a whole clip, or per time range (speed ramp), with optional frame interpolation for slow motion. |
| [Stabilization](../servers/render/stabilization/README.md) | 1 | Remove handheld shake with ffmpeg's two-pass vidstab. |
| [Timeline Project](../servers/render/timeline_project/README.md) | 1 | Render a simple edit in one call: clips with transitions, overlays on top, one mp4. |
