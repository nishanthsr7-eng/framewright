# Prompt: edit plan → DaVinci Resolve Lua script

Use a capable hosted model; small local models don't produce reliable scripts. Copy everything below the line, then paste your edit plan JSON at the end. The plan format is in [docs/edit-plan.md](../docs/edit-plan.md); an example is in [examples/edit_plan.example.json](../examples/edit_plan.example.json).

Save the reply as a `.lua` file in Resolve's `Fusion/Scripts/Edit/` folder, restart Resolve and run it from **Workspace → Scripts → Edit**. Lua works in Resolve Free without any Python install. See [docs/resolve-free-scripts.md](../docs/resolve-free-scripts.md) for how scripts get into Resolve and how to check they ran.

No LLM needed for the standard build: `resolve/scripts/Edit/Framewright/framewright_build_plan.lua` already builds any plan. Use this prompt when you want a custom script (different track layout, extra markers, partial rebuilds).

---

You are writing a Lua script for DaVinci Resolve 21's scripting API. It runs from Workspace → Scripts inside Resolve and builds a timeline from the edit plan at the end of this message.

## Output

- Reply with **one Lua code block only**, no explanation.
- Plain Lua 5.1. Embed the plan as a table literal: `local PLAN = { ... }` (convert the JSON; arrays become `{ ... }`, objects become `{ key = value }`, use `["in"]` for the `in` key because `in` is a Lua keyword).
- Use absolute file paths with forward slashes.

## Sandbox rules (Resolve 21.1 Free)

- Connect with the global: `local resolve = resolve or (fusion and fusion:GetResolve())`. `Resolve()` may return nil.
- `io` does not exist. Do not read or write files, and do not call `require`.
- Lists returned by the API can contain stray number values. Iterate them with this helper and nothing else:
  ```lua
  local function each(t)
      local out = {}
      for _, v in pairs(t or {}) do if type(v) ~= "number" and type(v) ~= "string" then out[#out + 1] = v end end
      return ipairs(out)
  end
  ```
- `print` output only shows if the Console is open. Collect messages in a table, and if anything failed, end with `error("report:\n" .. table.concat(msgs, "\n"))` so it is logged to `ResolveDebug.txt`.

## Steps the script must do

1. `local project = resolve:GetProjectManager():GetCurrentProject()`. If nil, `error` with "Open a project first".
2. `project:SetSetting("timelineFrameRate", ...)`, `"timelineResolutionWidth"`, `"timelineResolutionHeight"` with **string** values, before creating the timeline.
3. `local mp = project:GetMediaPool()`. Import every unique file from `clips` and `music` once with `mp:ImportMedia({path1, path2, ...})`. Map each to its item by `item:GetClipProperty("File Path")` (compare lowercased, with `\` turned into `/`). Reuse items already in the pool.
4. Create the timeline with `mp:CreateEmptyTimeline(name)`. If the name is taken (`project:GetTimelineByIndex(i):GetName()`), add `_2`, `_3`, ... Then `project:SetCurrentTimeline(timeline)`. Add video tracks with `timeline:AddTrack("video")` until the highest plan track exists.
5. Place each clip, sorted by `at`, with `mp:AppendToTimeline({{ ... }})`:
   - `mediaPoolItem`: the item
   - `startFrame`: `floor(in * src_fps + 0.5)`, where `src_fps = tonumber(item:GetClipProperty("FPS"))`
   - `endFrame`: `startFrame + length_frames - 1`. `length_frames` is the clip's slot on the timeline, `floor((at + (out - in) / speed) * fps + 0.5) - floor(at * fps + 0.5)`, converted to source frames (`* src_fps / fps`). The API cannot retime, so a slowed clip is placed at 1x for its full slot.
   - `trackIndex`: the plan's `track`
   - `recordFrame`: `timeline:GetStartFrame() + floor(at * fps + 0.5)`
   - `mediaType`: `1` (video only)
6. Place the music on audio track 1 at `timeline:GetStartFrame()` with `mediaType = 2`, cut to the video length.
7. Markers: `timeline:AddMarker(frame, color, name, "", 1)` with `frame = floor(at * fps + 0.5)` (relative to the timeline start). If it returns false, try `frame + 1` up to 10 times.
8. The API cannot add transitions, effects, speed changes or titles reliably. For each, add a marker at the clip's `at`:
   - Cyan `FX: <effect>`, Pink `TRANSITION: <type>`, Purple `SPEED: <speed>x (placed at 1x)`, Yellow `TITLE: <text>`
   - Then the plan's own `markers` with their colors.
9. Check: for each clip, find the timeline item on its track whose `item:GetStart() - timeline:GetStartFrame()` equals the planned frame, and whose `item:GetDuration()` is within 1 frame of the slot. Count misses.
10. If any import, placement or check failed, `error(...)` with the collected report.

## Rules

- Plan times are seconds; timeline frames use `PLAN.project.fps`, source frames use the clip's own fps.
- Check every API result. On nil/false, record a message and continue. Never stop halfway except in step 1.
- Never delete or change existing timelines or media.
- Use only the API calls named in this prompt.

## Edit plan

```json
PASTE YOUR EDIT PLAN HERE
```
