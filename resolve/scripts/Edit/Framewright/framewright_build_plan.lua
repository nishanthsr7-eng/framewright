-- Framewright: build a timeline from the latest edit plan, then check every clip landed on its frame.
-- Run in Resolve (Free or Studio): Workspace > Scripts > Edit > Framewright > framewright_build_plan. Output: Workspace > Console.
-- Reads <repo>/output/framewright_plan.lua, written by auto_amv_plan / build_edit_plan, or by prepare_resolve for an exact match of the render_plan MP4.
-- Lua, not Python, so it works even when Resolve can't find a Python install.

print(string.rep("=", 60))
-- Resolve 21.1: the `resolve` global is set, but Resolve() returns nil.
local resolve = resolve or (Resolve and Resolve()) or (fusion and fusion.GetResolve and fusion:GetResolve())
if not resolve then error("Framewright: cannot reach Resolve. Run this from Workspace > Scripts.") end
print("Resolve " .. resolve:GetVersionString())

-- Resolve 21.1 sandboxes Lua: no io, no env access. The repo path is baked in by resolve/install.ps1,
-- and print() only shows if the Console is open, so problems are also raised as an error at the end
-- (errors are logged to Support/logs/ResolveDebug.txt).
local ROOT = "__FRAMEWRIGHT_ROOT__"
local log_lines = {}
local _print = print
print = function(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
    log_lines[#log_lines + 1] = table.concat(parts, " ")
     _print(...)Z
end

local plan_file = ROOT .. "/output/framewright_plan.lua"
local ok, plan = pcall(dofile, plan_file)
if not ok or type(plan) ~= "table" then
    error("Framewright: no plan at " .. plan_file .. " (" .. tostring(plan) .. "). Make one with auto_amv_plan.")
end
print("Plan: " .. (plan.source or plan_file))

local proj_cfg = plan.project or {}
local fps = tonumber(proj_cfg.fps) or 24
local function to_frames(s) return math.floor(s * fps + 0.5) end

local project = resolve:GetProjectManager():GetCurrentProject()
if not project then print("Open a project first.") return end
-- Only takes effect on a project with no timelines yet; harmless otherwise.
project:SetSetting("timelineFrameRate", tostring(fps))
project:SetSetting("timelineResolutionWidth", tostring(proj_cfg.width or 1920))
project:SetSetting("timelineResolutionHeight", tostring(proj_cfg.height or 1080))
local mp = project:GetMediaPool()

-- Resolve's Lua lists can carry extra numeric fields; keep only API objects.
local function each(t)
    local out = {}
    for _, v in pairs(t or {}) do if type(v) ~= "number" and type(v) ~= "string" then out[#out + 1] = v end end
    return ipairs(out)
end

-- bin "Framewright"
local rootf = mp:GetRootFolder()
local bin
for _, f in each(rootf:GetSubFolderList() or {}) do if f:GetName() == "Framewright" then bin = f end end
bin = bin or mp:AddSubFolder(rootf, "Framewright")
if bin then mp:SetCurrentFolder(bin) end

-- import each file once (reuse items already in the bin)
local norm = function(p) return (p or ""):gsub("\\", "/"):lower() end
local items = {}
for _, it in each((bin or rootf):GetClipList() or {}) do items[norm(it:GetClipProperty("File Path"))] = it end
local want, seen = {}, {}
local function need(p) if p and not seen[norm(p)] and not items[norm(p)] then seen[norm(p)] = true; table.insert(want, p) end end
for _, c in ipairs(plan.clips or {}) do need(c.file) end
if plan.music then need(plan.music.file) end
if #want > 0 then
    for _, it in each(mp:ImportMedia(want) or {}) do items[norm(it:GetClipProperty("File Path"))] = it end
end
local skipped = {}
for _, p in ipairs(want) do if not items[norm(p)] then table.insert(skipped, "could not import " .. p) end end
-- title overlays from prepare_resolve carry straight alpha
for _, c in ipairs(plan.clips or {}) do
    local it = items[norm(c.file)]
    if c.alpha and it then it:SetClipProperty("Alpha mode", "Straight") end
end

-- timeline with a unique name
local name, taken = proj_cfg.name or "framewright", {}
for i = 1, project:GetTimelineCount() do taken[project:GetTimelineByIndex(i):GetName()] = true end
local final, n = name, 2
while taken[final] do final = name .. "_" .. n; n = n + 1 end
local timeline = mp:CreateEmptyTimeline(final)
if not timeline then print("Could not create timeline " .. final) return end
project:SetCurrentTimeline(timeline)
-- project settings only stick on a project without timelines, so also set them on this timeline
timeline:SetSetting("useCustomSettings", "1")
timeline:SetSetting("timelineFrameRate", tostring(fps))
timeline:SetSetting("timelineResolutionWidth", tostring(proj_cfg.width or 1920))
timeline:SetSetting("timelineResolutionHeight", tostring(proj_cfg.height or 1080))
local tl_fps = tonumber(timeline:GetSetting("timelineFrameRate"))
if tl_fps and math.abs(tl_fps - fps) > 0.01 then
    table.insert(skipped, string.format("timeline runs at %s fps, plan wants %s: use a new project", tl_fps, fps))
end
local max_track = 1
for _, c in ipairs(plan.clips or {}) do max_track = math.max(max_track, c.track or 1) end
while timeline:GetTrackCount("video") < max_track do timeline:AddTrack("video") end
local start = timeline:GetStartFrame()

local function src_fps(it) local v = tonumber(it:GetClipProperty("FPS")); return (v and v > 0) and v or fps end

local function add_marker(at_s, color, label)
    for off = 0, 9 do if timeline:AddMarker(to_frames(at_s) + off, color, label, "", 1) then return 1 end end
    return 0
end

-- place clips: frame-exact slot from plan.at to the next cut. Scripts can't retime, so slowed clips
-- are placed at 1x for their slot length and get a Purple SPEED marker. Plans from prepare_resolve
-- (plan.exact) have speed, flash and shake already baked into each cut, so nothing is marked missing.
local clips = {}
for _, c in ipairs(plan.clips or {}) do table.insert(clips, c) end
table.sort(clips, function(a, b) return a.at < b.at end)
local placed, markers = 0, 0
local expect = {}
for _, c in ipairs(clips) do
    local it = items[norm(c.file)]
    if it then
        local speed = c.speed or 1
        local sf = src_fps(it)
        local slot = to_frames(c.at + (c.out - c["in"]) / speed) - to_frames(c.at)
        local s_in = math.floor(c["in"] * sf + 0.5)
        local s_len = math.max(1, math.floor(slot * sf / fps + 0.5))
        local res = mp:AppendToTimeline({{mediaPoolItem = it, startFrame = s_in, endFrame = s_in + s_len - 1,
            trackIndex = c.track or 1, recordFrame = start + to_frames(c.at), mediaType = 1}})
        if res and #res > 0 then
            placed = placed + 1
            table.insert(expect, {track = c.track or 1, frame = to_frames(c.at), len = slot, at = c.at})
            if c.transition_in then markers = markers + add_marker(c.at, "Pink", "TRANSITION: " .. tostring(c.transition_in.type)) end
            for _, fx in ipairs(c.effects or {}) do markers = markers + add_marker(c.at, "Cyan", "FX: " .. fx) end
            if speed ~= 1 then markers = markers + add_marker(c.at, "Purple", "SPEED: " .. speed .. "x (placed at 1x)") end
        else
            table.insert(skipped, string.format("could not place %s at %.3fs", c.file, c.at))
        end
    end
end

-- music on A1 from the start, cut to the video length
local last = 0
for _, e in ipairs(expect) do last = math.max(last, e.frame + e.len) end
if plan.music and items[norm(plan.music.file)] then
    local it = items[norm(plan.music.file)]
    local sf = src_fps(it)
    local s_in = math.floor((plan.music.start or 0) * sf + 0.5)
    local res = mp:AppendToTimeline({{mediaPoolItem = it, startFrame = s_in,
        endFrame = s_in + math.floor(last * sf / fps + 0.5) - 1, trackIndex = 1, recordFrame = start, mediaType = 2}})
    if not (res and #res > 0) then table.insert(skipped, "could not place music") end
end

for _, t in ipairs(plan.titles or {}) do markers = markers + add_marker(t.at, "Yellow", "TITLE: " .. tostring(t.text)) end
for _, m in ipairs(plan.markers or {}) do markers = markers + add_marker(m.at, m.color or "Blue", m.name or "") end

print(string.format("Timeline: %s  |  placed %d/%d clips, %d markers", final, placed, #clips, markers))
for _, s in ipairs(skipped) do print("  skipped: " .. s) end

-- landing check: read the timeline back and compare with the plan
local good, bad = 0, 0
for track = 1, max_track do
    local at = {}
    for _, ti in each(timeline:GetItemListInTrack("video", track) or {}) do at[ti:GetStart() - start] = ti end
    for _, e in ipairs(expect) do
        if e.track == track then
            local ti = at[e.frame]
            if not ti then
                print(string.format("  MISS V%d %.3fs (frame %d): no clip starts there", track, e.at, e.frame)); bad = bad + 1
            elseif math.abs(ti:GetDuration() - e.len) > 1 then
                print(string.format("  LEN  V%d %.3fs: %d frames, plan wants %d", track, e.at, ti:GetDuration(), e.len)); bad = bad + 1
            else
                good = good + 1
            end
        end
    end
end
print(string.format("Landing check: %d clips on their frame, %d problems.", good, bad))
print(string.rep("=", 60))
if bad > 0 or #skipped > 0 or placed < #clips then
    error("Framewright report:\n" .. table.concat(log_lines, "\n"))
end
