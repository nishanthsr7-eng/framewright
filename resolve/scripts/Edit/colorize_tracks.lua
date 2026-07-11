-- Color-codes all video clips by their track number.
-- Run from Workspace > Scripts > Edit

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local trackColors = {
    "Orange", "Yellow", "Lime", "Teal",
    "Blue", "Purple", "Pink", "Tan"
}

local trackCount = tl:GetTrackCount("video")
local total = 0

for trackIdx = 1, trackCount do
    local color = trackColors[((trackIdx - 1) % #trackColors) + 1]
    local items = tl:GetItemListInTrack("video", trackIdx)
    if items then
        for _, item in ipairs(items) do
            item:SetClipColor(color)
            total = total + 1
        end
    end
end

print("Colorized " .. total .. " clips across " .. trackCount .. " tracks.")
