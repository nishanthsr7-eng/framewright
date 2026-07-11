-- Prints a summary of the current timeline: duration, tracks, clip count.
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local fps     = tonumber(tl:GetSetting("timelineFrameRate"))
local frames  = tl:GetEndFrame() - tl:GetStartFrame()
local secs    = frames / fps
local h = math.floor(secs / 3600)
local m = math.floor((secs % 3600) / 60)
local s = math.floor(secs % 60)

local vTracks = tl:GetTrackCount("video")
local aTracks = tl:GetTrackCount("audio")
local sTracks = tl:GetTrackCount("subtitle")

local totalClips = 0
for i = 1, vTracks do
    local items = tl:GetItemListInTrack("video", i)
    if items then totalClips = totalClips + #items end
end

local markers = tl:GetMarkers()
local markerCount = 0
if markers then for _ in pairs(markers) do markerCount = markerCount + 1 end end

print("=================================")
print("  Timeline: " .. tl:GetName())
print("=================================")
print("  Duration     " .. string.format("%02d:%02d:%02d", h, m, s) .. "  (" .. frames .. " frames)")
print("  Frame Rate   " .. fps .. " fps")
print("  Video Tracks " .. vTracks)
print("  Audio Tracks " .. aTracks)
print("  Subtitle Trk " .. sTracks)
print("  Total Clips  " .. totalClips)
print("  Markers      " .. markerCount)
print("=================================")
