# Workflow

From raw clips to a Resolve timeline. Steps 1-3 run through MCP; step 4 is a hosted API LLM; step 5 is Resolve.

## 1. Gather

Put clips and music in `input/`. Check what you have:

- `get_video_info` for each clip (duration, fps, size)
- `get_audio_info` for the music

## 2. Analyze

| Question | Tool |
|---|---|
| Where are the shots? | `detect_scenes` (anime: try `threshold` around 20) |
| Where are the beats and bars? | `detect_beats`, `detect_downbeats` |
| Where does the song build and drop? | `detect_sections`, `detect_impacts` |
| What is said, and when? | `transcribe_audio` (word timestamps) |
| Which moments are loudest? | `generate_highlights` |

## 3. Prepare assets (optional)

- Upscale: `extract_frames_from_video` → `enhance_frames`
- Cut out a subject: `extract_subject(style="anime" | "general")`
- Key a green screen: `remove_background`
- Titles and captions: `add_text_overlay`, `add_karaoke_captions` (transparent `.webm`)
- Pre-render looks Resolve can't do easily: `apply_effect`, `apply_lut`, `speed_ramp`, `stabilize_video`

## 4. Plan and script

1. Collect the results into an edit plan JSON: [edit-plan.md](edit-plan.md). An example lives in `examples/`. `build_edit_plan` drafts one with cuts on the beat; run `validate_plan` on it (and again after LLM or hand edits).
2. Preview it with `render_plan`, then run `prepare_resolve` on the same plan (same `platform`). It bakes speed, flashes, shakes and the crop into each cut, turns titles into transparent overlays and writes `output/framewright_plan.lua`.
3. Need logic the standard build doesn't cover? Give the plan and `prompts/resolve-script.md` to a capable hosted API model (e.g. GPT- or Claude-class) for a custom Lua script. Small local models are not supported: they don't write reliable Resolve scripts.

You can also ask the LLM to write the plan itself from the analysis output; review it before step 5.

## 5. Build in Resolve

In a new project, run **Workspace → Scripts → Edit → Framewright → framewright_build_plan** ([resolve-free-scripts.md](resolve-free-scripts.md)). It creates a timeline at the plan's size and frame rate, places every cut on its frame (V1), the titles above it, the music on A1 and checks each clip landed where the plan says. The result matches the `render_plan` preview. Then finish by hand: Fusion templates, grading, mix.

A custom LLM script goes in Resolve's `Scripts/Edit` folder and runs from the same menu ([resolve.md](resolve.md)).

## No Resolve?

Use the render servers end to end: `timeline_project` (or `compose_layers`) → `apply_lut` → `normalize_loudness` / `add_background_music` → `export_for_platform`.

## Example

> "Cut these three clips to the drop of this song, one shot per two beats, flash white on each downbeat after the drop, title 'FINALLY FREE' at the drop, export 9:16."

1. `detect_scenes` on each clip, `detect_downbeats` + `detect_sections` on the song.
2. Build the plan: shots on every second beat from the drop, Flash White transitions on downbeats, one title.
3. `render_plan(platform="tiktok")` to preview, `prepare_resolve(platform="tiktok")`, then `framewright_build_plan` in Resolve; export with Resolve's 9:16 render preset or `export_for_platform(platform="tiktok")`.
