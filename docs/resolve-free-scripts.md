# Running Framewright scripts in DaVinci Resolve Free

How an edit plan gets from the MCP tools into a Resolve timeline without Resolve Studio, and how to check it worked. Tested on Resolve 21.1.1 Free, Windows.

## The flow

```
auto_amv_plan / build_edit_plan          (MCP, beat_sync server)
  ├─ output/<music>/amv_plan.json        the plan (docs/edit-plan.md)
  └─ output/framewright_plan.lua         same plan as a Lua table, absolute paths
                │
prepare_resolve                          (MCP, timeline_project; optional, for an exact match)
  ├─ output/resolve/<plan>_<time>/       each cut baked as render_plan draws it, titles as alpha .mov, music.wav
  └─ output/framewright_plan.lua         overwritten: places those files 1:1
                │
resolve/install.ps1                      (once, or after editing scripts)
  └─ copies resolve/scripts/* to Resolve's Fusion/Scripts/
     and writes the repo path into the installed framewright_build_plan.lua
                │
Resolve: Workspace > Scripts > Edit > Framewright > framewright_build_plan
  └─ dofile(<repo>/output/framewright_plan.lua) → import → timeline → markers → landing check
```

Every new plan overwrites `output/framewright_plan.lua`, so the script always builds the **latest** plan. To rebuild an older one, re-run the plan tool or `prepare_resolve` on it, or call `write_plan_lua` in `beat_sync_mcp/plan.py`.

## Why Lua, not Python

- Free can't run scripts from a terminal (that "external scripting" needs Studio). Scripts must be started from inside Resolve.
- Resolve only lists `.py` scripts when it finds a Python install it accepts. That changes between versions: 21.0 found a per-user Python 3.10, but 21.1.1 did not, so every `.py` script silently disappeared from the menu.
- Lua is built into Resolve, so `.lua` scripts always show up.

## Install

```bash
powershell -ExecutionPolicy Bypass -File resolve\install.ps1
```

- Copies into `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Edit\` (and `Utility\`, templates).
- Replaces `__FRAMEWRIGHT_ROOT__` in the installed `framewright_build_plan.lua` with the repo path (no BOM, Lua rejects it). Re-run after moving the repo.
- **Restart Resolve fully** afterwards. It only scans the Scripts folder at startup. Check Task Manager: two `Resolve.exe` processes means a stuck copy; end both and start once.

## Lua sandbox rules (Resolve 21.1)

| Works | Doesn't |
|---|---|
| `resolve` global (the Resolve object) | `Resolve()` returns nil |
| `dofile(path)`, `os`, `pcall`, `error` | `io` is nil (no file read/write) |
| `fusion`, `bmd` | `bmd.writefile` missing, `bmd.readfile` fails |
| `print` (only if the Console is open) | env vars via the script's own folder (unknown path) |

- That's why the plan is a `.lua` file starting with `return { ... }` (loaded with `dofile`), and the repo path is baked in at install.
- API lists can contain stray number entries. Filter them (`each()` helper in the script) before calling methods, or you get `attempt to index ... (a number value)`.
- No `AppendToTimeline` retime and no transition API: from a plain plan, slowed clips are placed at 1x for their slot with a Purple `SPEED` marker, and transitions, effects and titles become markers. Run `prepare_resolve` first to get them for real: it bakes them into the media, so the timeline matches the `render_plan` MP4 frame for frame.
- Project settings only stick on a project with no timelines, so the script also sets size and frame rate on the new timeline (`useCustomSettings`). If the frame rate still differs, it stops and asks for a new project.

## Checking it worked

1. On the Edit page: a new timeline named `<project name>` (or `_2`, `_3`), clips on V1, titles on V2+ (from `prepare_resolve`), music on A1, colored markers.
2. Errors and the report: the script raises `error()` when anything is skipped or lands on the wrong frame. Resolve writes that to
   `%APPDATA%\Blackmagic Design\DaVinci Resolve\Support\logs\ResolveDebug.txt` (search for `framewright_build_plan.lua:`). No new line there after a run = every clip placed and on its frame.
3. With the Console open (F6) before running, the full report prints there too, ending with `Landing check: N clips on their frame, 0 problems.`

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Script not in the menu | Resolve not restarted after install, or a stuck second `Resolve.exe` |
| Clicking does nothing, Console empty | Read `ResolveDebug.txt`; the error is there, not in the Console |
| `no plan at ...` | Run `auto_amv_plan` (or `build_edit_plan`) first |
| `cannot reach Resolve` | Run from Workspace > Scripts, not the Console's Lua prompt in another app |
| `attempt to index ... (a number value)` | Iterating an API list without the `each()` filter |
| `timeline runs at X fps, plan wants Y` | Make a new project; an existing one can lock the frame rate |
| Titles show a black box | Select the title clips, Clip Attributes > Alpha mode > Straight |
| Resolve closes during "Loading Edit Page"; `ResolveDebug.txt` says `Memory allocation failed` | Windows is out of memory. Close other apps, or extra MCP client sessions (each starts every Framewright server, ~5 GB per set) |
| Clips land but some are short | Source shot is shorter than the slot; check `clips[i].out` against the file length with `validate_plan` |

## Custom scripts from an LLM

`prompts/resolve-script.md` asks a capable hosted LLM for a Lua script that follows the same rules. Save the reply as `Fusion/Scripts/Edit/<name>.lua`, restart Resolve, run it from the menu and check `ResolveDebug.txt` the same way.
