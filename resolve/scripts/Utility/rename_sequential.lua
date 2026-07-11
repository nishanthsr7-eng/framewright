-- Renames all video clips in the timeline as Clip_001, Clip_002, ...
-- Clips are numbered left-to-right, top track first.
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local vTracks = tl:GetTrackCount("video")
local count = 0

for track = 1, vTracks do
    local items = tl:GetItemListInTrack("video", track)
    if items then
        table.sort(items, function(a, b) return a:GetStart() < b:GetStart() end)
        for _, item in ipairs(items) do
            count = count + 1
            item:SetName(string.format("Clip_%03d", count))
        end
    end
end

print("Renamed " .. count .. " clips.")
