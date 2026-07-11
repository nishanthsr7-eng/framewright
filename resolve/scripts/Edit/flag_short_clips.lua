-- Flags clips shorter than a threshold with Red color so you can spot them easily.
-- Useful before export to find micro-clips that may cause render issues.

local MIN_FRAMES = 6   -- change this: clips shorter than this get flagged

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local fps        = tonumber(timeline:GetSetting("timelineFrameRate"))
local trackCount = timeline:GetTrackCount("video")
local flagged    = 0
local total      = 0

for t = 1, trackCount do
    local items = timeline:GetItemListInTrack("video", t)
    if items then
        for _, item in ipairs(items) do
            total = total + 1
            local len = item:GetEnd() - item:GetStart()
            if len < MIN_FRAMES then
                item:SetClipColor("Red")
                flagged = flagged + 1
                print(string.format("  SHORT: '%s' on V%d — %d frame(s)", item:GetName(), t, len))
            end
        end
    end
end

print(string.format("\nScanned %d clips. Flagged %d clip(s) shorter than %d frames in Red.",
    total, flagged, MIN_FRAMES))
if flagged == 0 then
    print("No short clips found. All good!")
end
