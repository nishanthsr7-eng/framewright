-- Scans the timeline and prints every gap (empty region on video tracks).
-- Useful for finding unwanted holes before export.
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local fps = tonumber(tl:GetSetting("timelineFrameRate"))
local startFrame = tl:GetStartFrame()
local endFrame   = tl:GetEndFrame()
local vTracks    = tl:GetTrackCount("video")
local gapCount   = 0

local function toTC(frame)
    local secs = frame / fps
    local h = math.floor(secs / 3600)
    local m = math.floor((secs % 3600) / 60)
    local s = math.floor(secs % 60)
    return string.format("%02d:%02d:%02d", h, m, s)
end

for track = 1, vTracks do
    local items = tl:GetItemListInTrack("video", track)
    if not items or #items == 0 then goto continue end

    table.sort(items, function(a, b) return a:GetStart() < b:GetStart() end)

    -- Gap before first clip
    if items[1]:GetStart() > startFrame then
        local gapLen = items[1]:GetStart() - startFrame
        print(string.format("V%d  GAP at %s  len=%d frames", track, toTC(startFrame), gapLen))
        gapCount = gapCount + 1
    end

    -- Gaps between clips
    for i = 1, #items - 1 do
        local tail = items[i]:GetEnd()
        local head = items[i+1]:GetStart()
        if head > tail then
            local gapLen = head - tail
            print(string.format("V%d  GAP at %s  len=%d frames", track, toTC(tail), gapLen))
            gapCount = gapCount + 1
        end
    end

    ::continue::
end

if gapCount == 0 then
    print("No gaps found. Timeline is clean.")
else
    print("\n" .. gapCount .. " gap(s) found.")
end
