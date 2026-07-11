-- Adds a yellow marker at the start of every clip on V1 — instant scene map.
-- Run this after rough cut to visualize all cut points.

local MARKER_COLOR = "Yellow"

local resolve = Resolve()
local pm      = resolve:GetProjectManager()
local project = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local fps       = tonumber(timeline:GetSetting("timelineFrameRate"))
local startTC   = timeline:GetStartFrame()
local existing  = timeline:GetMarkers() or {}

local items = timeline:GetItemListInTrack("video", 1)
if not items then
    print("No clips on V1.")
    return
end

local added = 0
local skipped = 0

for i, item in ipairs(items) do
    local frame  = item:GetStart() - startTC
    local name   = "Scene " .. i
    if existing[frame] then
        skipped = skipped + 1
    else
        local ok = timeline:AddMarker(frame, MARKER_COLOR, name, "", 1)
        if ok then added = added + 1 end
    end
end

print(string.format("Done. Added %d scene markers, skipped %d (already had a marker).", added, skipped))
print("TIP: Rename each marker in the timeline to label your scenes.")
