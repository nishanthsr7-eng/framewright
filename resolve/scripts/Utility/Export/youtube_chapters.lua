-- Exports all timeline markers as YouTube chapter timestamps.
-- Paste the output directly into a YouTube video description.
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local fps = tonumber(tl:GetSetting("timelineFrameRate"))
local markers = tl:GetMarkers()

if not markers then
    print("No markers found in timeline.")
    return
end

-- Collect and sort marker frames
local frames = {}
for frameId, _ in pairs(markers) do
    table.insert(frames, frameId)
end
table.sort(frames)

local function toYT(frame)
    local secs = math.floor(frame / fps)
    local h = math.floor(secs / 3600)
    local m = math.floor((secs % 3600) / 60)
    local s = secs % 60
    if h > 0 then
        return string.format("%d:%02d:%02d", h, m, s)
    else
        return string.format("%d:%02d", m, s)
    end
end

print("--- YouTube Chapters ---")
for _, frame in ipairs(frames) do
    local marker = markers[frame]
    local ts = toYT(frame)
    local name = (marker.name and marker.name ~= "") and marker.name or "Chapter"
    print(ts .. " " .. name)
end
print("------------------------")
print(#frames .. " chapters exported.")
