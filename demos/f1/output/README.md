# F1 demo outputs

Versions in order. Each folder: final video `f1_edit_v0N.mp4`, the script that made it, `analysis/` sheets,
and intermediates in `_work/` (needed to re-render; safe to delete only if you accept a full re-render).

| Version | Folder | What it is |
|---|---|---|
| v01 | `v01_plan/` | First edit plan (JSON only, no render) |
| v02 | `v02_preview/` | Plan v2 and its preview render |
| v03 | `v03_reference_recreate/` | Reference edit's structure and look recreated with ffmpeg; subject cut-out frames in `_work/` |
| v04 | `v04_transitions_titles/` | v03 + transitions, beat pulses, cut-out glow, kinetic title, Framewright finishing |
| v05 | `v05_loop_60fps/` | 60 fps reference-style edit that loops seamlessly; `resolve_export/` = the same edit for DaVinci Resolve |

Shared:
- `shared/f1_audio.wav` — the song, used by every version
- `footage_analysis/` — contact sheets of the source footage
- `reference_analysis/` — contact sheets of `input/reference_edit.mp4`

Dependencies: v04 reads `v03_reference_recreate/_work/subject_rgba`; v05 imports `v04_transitions_titles/render_f1_v04.py`.

Re-render (from the repo root):
- v05: `uv run --directory servers/render/overlay_fx python demos/f1/output/v05_loop_60fps/render_f1_v05.py`
- v05 for Resolve: same with `resolve_f1_v05.py` (add `--plan-only` to just rewrite `output/framewright_plan.lua`)
