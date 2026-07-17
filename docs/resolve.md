# DaVinci Resolve

Framewright ends in DaVinci Resolve. Three parts live in `resolve/`:

| Folder | What | Edition |
|---|---|---|
| `resolve/templates/` | 90 Fusion templates: 42 titles, 27 effects, 16 transitions, 5 generators | Free and Studio |
| `resolve/scripts/` | 20 Lua scripts (Edit + Utility) | Free and Studio |
| `resolve/bridge/` | Python helpers imported by LLM-generated scripts | Free and Studio |

## Install

Enable scripting first: Preferences → System → General → **External scripting using = Local**, then restart Resolve.

Run the installer from the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File resolve\install.ps1
```

```bash
bash resolve/install.sh
```

Options: `-Uninstall` / `--uninstall` removes only the files this repo installs; `-DryRun` / `--dry-run` shows what would change; `-Dest` / `--dest` sets a custom Fusion folder.

It copies into Resolve's per-user Fusion folder:

| OS | Fusion folder |
|---|---|
| Windows | `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\` |
| macOS | `~/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/` |
| Linux | `~/.local/share/DaVinciResolve/Fusion/` |

- `resolve/scripts/Edit`, `Utility` → `<Fusion>/Scripts/Edit`, `Utility`
- `resolve/templates/*` → `<Fusion>/Templates/Edit/{Titles,Effects,Transitions,Generators}`

Quit and reopen Resolve to refresh the Effects panel.

## Running an LLM-generated script

1. Run the analysis servers and build an edit plan ([edit-plan.md](edit-plan.md)).
2. Give the plan and `prompts/resolve-script.md` to any LLM. It returns a Python script.
3. Save it into `<Fusion>/Scripts/Edit/` and run it from **Workspace → Scripts**. This works in the free edition.
4. Studio only: you can also run it from a terminal with Resolve's external scripting API.

Full flow: [workflow.md](workflow.md).

## Where templates appear

| Type | In Resolve |
|---|---|
| Titles | Edit page → Effects → Toolbox → Titles |
| Transitions | Effects → Video Transitions → Fusion Transitions |
| Effects | Effects → Effects → Fusion Effects |
| Generators | Effects → Generators |
| Scripts | Workspace → Scripts → Edit / Utility |

## Templates

- **Titles (42):** basic and lower thirds, animated (fade, slide, pop, bounce, typewriter), 3D-look (chrome, gold, neon, fire, extruded), overlays (cinematic bars, social follow, podcast, score bar, news ticker, countdown, chat bubble, meme caption), FX (speed lines, lens flare hit, matrix rain, logo reveal, split text reveal).
- **Effects (27):** impact (Screen Shake, Zoom Punch, Chromatic Aberration, Afterimage Echo), grades (Teal Orange, High Contrast, Bleach Bypass, Neon Cyberpunk, Duotone, BW Color Pop), looks (Film Grain, Film Halation, VHS Retro, Old Film, Lo-Fi Dreamy, Soft Glow, Vignette, Vignette Pulse), overlays (Light Rays, Rain, Bokeh, Anamorphic Flare Streaks) and more.
- **Transitions (16):** Dip to Black/White, Cross Blur, Flash White/Black, Whip Pan Right, Zoom Blur Cut, Glitch Cut, Spin Rotate, Slide Push Left, Circle Iris, Strobe Cut, Color Wipe, Pixel Scatter, Flip Horizontal, Light Leak.
- **Generators (5):** Animated Gradient, Aurora Northern Lights, Electric Sparks, Glitch Bars, Starfield.

## Lua scripts

**Edit:** `add_interval_markers`, `auto_scene_markers`, `batch_add_effect`, `beat_sync_prep`, `colorize_tracks`, `copy_grade_to_track`, `flag_short_clips`, `insert_flash_frames`, `remove_all_markers`, `set_all_duration`.

**Utility:** `timeline_stats`, `find_gaps`, `export_clip_list`, `export_markers_csv`, `youtube_chapters`, `organize_media_pool`, `duplicate_timeline`, `rename_sequential`, `clear_clip_colors`, `count_clip_usage`.

Output appears in Workspace → Console.

## Effect recipes

| Moment | Stack |
|---|---|
| Hit / landing | Screen Shake + Chromatic Aberration, cut with Flash White (12-20 frames) |
| Speed burst | Zoom Punch + FX Speed Lines, cut with Zoom Blur Cut |
| Explosion | Screen Shake + FX Lens Flare Hit + High Contrast Grade |
| Flashback | VHS Retro + Soft Glow, Dip to White |
| Reveal | Vignette Pulse + High Contrast Grade, Flash Black |

These suit both anime and live-action edits; keep impact frames 2-4 frames long.
