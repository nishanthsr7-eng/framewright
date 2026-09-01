-- Removes all clip color flags from every video clip in the timeline.
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
        for _, item in ipairs(items) do
            item:SetClipColor("")
            count = count + 1
        end
    end
end

print("Cleared colors from " .. count .. " clips.")
