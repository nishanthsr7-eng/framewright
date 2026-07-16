# Prompt: edit plan → DaVinci Resolve script

Works with any LLM (ChatGPT, Claude, Gemini, local models). Copy everything below the line, then paste your edit plan JSON at the end. The plan format is in [docs/edit-plan.md](../docs/edit-plan.md); an example is in [examples/edit_plan.example.json](../examples/edit_plan.example.json).

Save the reply as a `.py` file in Resolve's `Fusion/Scripts/Edit/` folder and run it from **Workspace → Scripts** (works in Resolve Free).

---

You are writing a Python script for DaVinci Resolve's scripting API. It builds a timeline from the edit plan JSON at the end of this message.

## Output

- Reply with **one Python code block only**, no explanation.
- Python 3, standard library only. Embed the plan as a dict literal named `PLAN`.

## Connecting

```python
try:
    resolve = app.GetResolve()  # when run from Workspace → Scripts
except NameError:
    import DaVinciResolveScript as dvr  # when run from a terminal (Studio)
    resolve = dvr.scriptapp("Resolve")
```

## Steps the script must do

1. Get the project manager and the current project. If there is none, create one named `PLAN["project"]["name"]`.
2. Set `timelineFrameRate`, `timelineResolutionWidth` and `timelineResolutionHeight` with `project.SetSetting(...)` **before** creating the timeline. Values are strings.
3. Import every unique file from `clips`, `music` and other plan entries with `media_pool.ImportMedia([...])`. Convert paths to absolute paths with `os.path.abspath`. Map each path to its `MediaPoolItem`.
4. Create the timeline with `media_pool.CreateEmptyTimeline(name)` and make it current with `project.SetCurrentTimeline(timeline)`.
5. Place clips with `media_pool.AppendToTimeline([...])`, one dict per clip:
   - `mediaPoolItem`: the imported item
   - `startFrame`, `endFrame`: source in and out, `round(seconds * source_fps)` (read the source fps with `item.GetClipProperty("FPS")`)
   - `trackIndex`: the plan's `track`
   - `recordFrame`: `timeline.GetStartFrame() + round(at * fps)`
   - `mediaType`: `1` for the video part of video clips
6. Place the music on audio track 1 at the timeline start, with `mediaType` `2`.
7. Add each plan marker with `timeline.AddMarker(frame, color, name, note, 1)`. `frame` is relative to the timeline start: `round(at * fps)`.
8. Titles: move the playhead with `timeline.SetCurrentTimecode(...)` to the title's `at`, then call `timeline.InsertFusionTitleIntoTimeline(template)`. If that returns `None`, add a Yellow marker named `TITLE: <text>` instead.
9. The API cannot add transitions, effects or speed changes. For each one, add a marker at the clip's `at` so the editor can apply it by hand:
   - Cyan `FX: <effect>` for effects
   - Pink `TRANSITION: <type> <frames>f` for transitions
   - Purple `SPEED: <speed>x` when speed ≠ 1.0
10. At the end, print a summary: the number of clips placed, the markers added, and anything skipped.

## Rules

- Times in the plan are seconds. Convert them to frames with `PLAN["project"]["fps"]`, except source in/out frames, which use the source clip's fps.
- Check each API call. If it returns `None` or `False`, print a clear message and continue with the next item. Never crash halfway.
- Do not delete or change existing timelines. If the timeline name is taken, add `_2`, `_3` and so on.
- Use only API calls named in this prompt.

## Edit plan

```json
PASTE YOUR EDIT PLAN HERE
```
