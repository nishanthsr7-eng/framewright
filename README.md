# Framewright

**Let an AI do the tedious part of a video edit: beat-syncing, cutouts, captions. Then finish the cut yourself in DaVinci Resolve.**

https://github.com/user-attachments/assets/884fd6ba-7747-45fc-98e4-92a29a5fe29d

<sub>720p preview. **[View full video](FULL_VIDEO_URL)** in full quality.</sub>

Framewright is a set of small Python tools that an AI assistant can call over the **Model Context Protocol (MCP)**. They listen to the music, find the shots, transcribe speech and cut out subjects. The AI then turns those results into an edit plan and a DaVinci Resolve script that builds the timeline. It needs a capable hosted API model (GPT- or Claude-class); small local models can't write reliable Resolve scripts and aren't supported.

---

## Why it exists

- Most of an edit's hours go to mechanical work: finding beats, lining cuts up to them, rotoscoping, typing captions.
- AI video generators replace the editor; Framewright keeps the editor and removes the busywork.
- **For editors who want an AI to do the tedious 80% (beat-syncing, cutouts, captions) while keeping the final cut in Resolve.**

---

## What it can do

| Area | Highlights |
|---|---|
| Analysis | Beats, downbeats, song sections, impacts, local speech-to-text with word timestamps, shot detection, audio-based highlight picking |
| Assets | Frame extraction, Real-ESRGAN upscaling, subject cutouts (ISNet for anime, U2-Net for general, opt-in BiRefNet-lite `general_hq` for sharper hair/edges), chroma key, animated titles, karaoke captions |
| Render | Editing effects and xfade transitions, 7 cinematic LUTs, color matching, film-look overlays, speed ramps, stabilization, Ken Burns, compositing, loudness/ducking, platform export presets |
| Plans | Draft (`build_edit_plan`, `auto_amv_plan`), check (`validate_plan`), preview (`render_plan`), send to Resolve (`prepare_resolve`) |
| Resolve | 90 Fusion templates (titles, effects, transitions, generators) and 21 Lua scripts; all work in the free edition |

Model-based tools take `style="anime" | "general"`, so both animation and live-action footage work. Every server and tool: [docs/README.md](docs/README.md).

---

## Requirements

| Need | Notes |
|---|---|
| OS | Windows, Linux or macOS |
| Python | 3.10+ (managed by `uv`) |
| [uv](https://docs.astral.sh/uv/) | installs the workspace |
| ffmpeg + ffprobe | on PATH |
| GPU (optional) | NVIDIA for faster subject cutouts; Vulkan for Real-ESRGAN upscaling |
| Disk | ~0.5 GB for models (`scripts/fetch_models.py`), more with `birefnet` |
| DaVinci Resolve (optional) | free edition is enough; without it, use `render_plan` and the render servers |

## Quick start

1. Install `ffmpeg` and `uv`.
2. Run setup. It installs every server, downloads models, creates `.mcp.json` and runs a smoke test:
   - Windows: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`
   - Linux/macOS: `bash scripts/setup.sh`
3. Point your MCP client at `.mcp.json`.

Details: [docs/setup.md](docs/setup.md). CPU-only check without installing anything locally: `docker build -t framewright . && docker run --rm framewright` (starts all 19 servers and lists their tools).

---

## How it works

```mermaid
flowchart LR
    M[Clips + music] --> A[Analysis servers<br/>beats, scenes, speech]
    M --> S[Asset servers<br/>cutouts, captions, upscaling]
    A --> P[Edit plan JSON]
    S --> P
    P --> V{validate_plan}
    V --> R[render_plan<br/>preview MP4]
    V --> X[prepare_resolve] --> D[DaVinci Resolve<br/>timeline]
```

**Design decisions** (more in [docs/architecture.md](docs/architecture.md)):

- **Many small servers, not one big one.** Each has its own dependencies, so the heavy ones (torch, ONNX, Whisper) only install where needed.
- **The edit plan is the contract.** A JSON file the LLM, the validator, the previewer and Resolve all read, so each step can be checked on its own.
- **Resolve stays in charge of the final cut.** Tools prepare media; the editor finishes by hand.
- **Frame-exact cuts.** Cuts are snapped to frames, then to detected onsets, so they land on the beat.

Why each choice was made: [docs/decisions/](docs/decisions/README.md).

---

## Results

Measured on synthetic, license-free fixtures with known ground truth (`evals/`). The numbers compare tools and catch regressions; they are not claims about every kind of footage. CI fails if beat-sync or scene results regress.

| Eval | Metric | Result |
|---|---|---|
| Beat-synced cuts (90/120/140 BPM, 25 fps) | cuts > 1 frame off the beat | **0 / 114** (was 89 / 114); mean error ≈ 10 ms, worst 26 ms |
| Beat detection | F-measure (mir_eval, ±70 ms) | 1.000 / 0.987 / 1.000 |
| Scene cuts (5 hard cuts) | precision / recall | 1.000 / 1.000 |
| Scene cuts, hard set (2 dissolves, 3 hard cuts incl. near-identical greys) | precision / recall | 1.000 / 0.600 (not a CI gate) |
| Transcription (Whisper base, CPU) | word error rate | 0.026 |
| Subject cut-out, anime set (20 frames) | mean IoU: anime model / general model | 0.604 / 0.528 |
| Subject cut-out, live-action set (20 frames) | mean IoU: general model / anime model | 0.762 / 0.437 |

How 89/114 became 0/114: [docs/case-study-beat-sync.md](docs/case-study-beat-sync.md).

Reproduce (needs ffmpeg; each eval runs in the server it tests):

```bash
python scripts/run_evals.py        # beat-sync + scenes
python scripts/run_evals.py all    # + beat F-measure, WER, segmentation
```

### Performance

Seconds of processing per minute of 1080p footage at 24 fps (lower is better). Measured on a laptop with a Ryzen 9 8940HX and an RTX 5050 Laptop GPU, on a short synthetic clip, so treat these as rough numbers.

| Tool | GPU | CPU |
|---|---|---|
| Subject cut-out, `anime` (ISNet) | 338 | 969 |
| Subject cut-out, `general` (U2-Net) | 231 | 455 |
| Subject cut-out, `general_hq` (BiRefNet lite) | 1475 | 7904 |
| Whisper base transcription (per minute of audio) | 2 | 6 |
| Real-ESRGAN x2, `realesr-animevideov3` (Vulkan) | 9674 (includes model load) | - |
| Stabilization (vid.stab, two passes) | - | 80 |

Run it on your machine: `uv run python scripts/benchmark.py --frames 48`.

### Cost of one edit (Claude Opus 5.5)

These are real numbers taken from the session logs of the F1 demo edit, not estimates. They cover the whole job, from setup and the first plan, through refining it (v03–v05), to landing the timeline in Resolve. Cost uses API list prices. Most input came from the prompt cache, which keeps the total low.

| | Setup + first plan (v01–v02) | Refine (v03–v05) | Land in Resolve | **Total** |
|---|---|---|---|---|
| Your prompts | 3 | 6 | 3 | **12** |
| Model requests | 41 | 155 | 32 | **228** |
| Tool calls | 47 | 186 | 32 | **265** |
| Output tokens | 22.1K | 203.1K | 32.8K | **258.0K** |
| Cached input read | 3.6M | 13.4M | 2.8M | **19.8M** |
| Cache writes (1 h) | 131.8K | 515.6K | 95.7K | **743.1K** |
| Cost at API list price | $2.21 | $10.87 | $1.98 | **$15.06** |

---

## Limitations

- Subject cutouts on macOS run on CPU only.
- Real-ESRGAN upscaling needs a Vulkan-capable GPU.
- Anime cutout IoU is 0.60 on synthetic frames; expect touch-ups on hard shots.
- `general_hq` (BiRefNet) is slow: about 7 s per frame on CPU.
- The free edition of Resolve has no live remote control; you run the generated script from Resolve's Scripts menu.
- Scene detection misses dissolves and near-identical shots (recall 0.60 on the hard set).

## Roadmap

Planned work is tracked in [GitHub issues](https://github.com/nishanthsr7-eng/Video_Editor-MCP/issues).

---

## Layout

```
servers/core/       framewright_core: shared ffmpeg, probe, paths, error helpers
servers/analysis/   audio_analyzer, scene_detector, beat_sync, highlight_reel
servers/assets/     frame_extractor, subject_extractor, chroma_key, text_overlay
servers/render/     effects, lut_grading, color_match, compositor, overlay_fx, speed_ramp,
                    stabilization, ken_burns, audio_mastering, export_presets, timeline_project
resolve/            Lua scripts, Fusion templates, bridge/ (helpers for generated scripts)
prompts/            Prompt templates for the LLM step
examples/           Example edit plans
demos/              Worked examples
evals/              Synthetic fixtures and accuracy evals
tests/              Unit and ffmpeg integration tests
scripts/            Setup, model download, smoke test, eval runner
docs/               Documentation
models/             Model weights (downloaded, not in git)
```

**Original vs vendored:** `servers/assets/frame_extractor` is vendored from [video-creator/ffmpeg-mcp](https://github.com/video-creator/ffmpeg-mcp) (MIT); its README lists what changed. Everything else is original to this repo.

---

## Docs

- [Setup](docs/setup.md): install, models, MCP client config
- [Workflow](docs/workflow.md): from raw clips to a Resolve timeline
- [Architecture](docs/architecture.md): how the pieces fit
- [Edit plan](docs/edit-plan.md): the JSON format the LLM works from
- [DaVinci Resolve](docs/resolve.md): templates, scripts, install
- [Servers](docs/README.md): every server and tool
- [Third-party](docs/third-party.md): vendored code, models, fonts
- [Credits](CREDITS.md): demo footage and music

## Contributing

Lint and test before a PR:

```bash
uv run --only-group dev ruff check . && uv run --only-group dev ruff format --check .
uv run --only-group test pytest
```

How to add a server, code rules and tests: [CONTRIBUTING.md](CONTRIBUTING.md). Security reports and why to read generated scripts first: [SECURITY.md](SECURITY.md). Release history: [CHANGELOG.md](CHANGELOG.md).

## License and credits

MIT, see [LICENSE](LICENSE). Vendored code, models, fonts and demo media keep their own licenses; see [CREDITS.md](CREDITS.md).
