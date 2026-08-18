# Workflow

From raw clips to a Resolve timeline. Steps 1-3 run through MCP; step 4 is any LLM; step 5 is Resolve.

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

1. Collect the results into an edit plan JSON: [edit-plan.md](edit-plan.md). An example lives in `examples/`. `build_edit_plan` drafts one with cuts on the beat; run `validate_plan` on it (and again after any LLM or hand edits).
2. Give the plan and `prompts/resolve-script.md` to any LLM (ChatGPT, Claude, Gemini, local models).
3. It returns a Python script that uses `resolve/bridge` helpers.

You can also ask the LLM to write the plan itself from the analysis output; review it before step 5.

## 5. Build in Resolve

Save the script to Resolve's `Scripts/Edit` folder and run it from **Workspace → Scripts** ([resolve.md](resolve.md)). Resolve creates the timeline, places clips on beats, and adds markers and titles. Then finish by hand: Fusion templates, grading, mix.

## No Resolve?

Use the render servers end to end: `timeline_project` (or `compose_layers`) → `apply_lut` → `normalize_loudness` / `add_background_music` → `export_for_platform`.

## Example

> "Cut these three clips to the drop of this song, one shot per two beats, flash white on each downbeat after the drop, title 'FINALLY FREE' at the drop, export 9:16."

1. `detect_scenes` on each clip, `detect_downbeats` + `detect_sections` on the song.
2. Build the plan: shots on every second beat from the drop, Flash White transitions on downbeats, one title.
3. LLM writes the Resolve script; run it; export with Resolve's 9:16 render preset or `export_for_platform(platform="tiktok")`.
