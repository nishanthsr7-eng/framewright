-- Adds chapter markers every N seconds across the whole timeline.
-- Change INTERVAL_SECONDS below to adjust spacing.
-- Run from Workspace > Scripts > Edit

local INTERVAL_SECONDS = 5
local MARKER_COLOR = "Blue"

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local fps = tonumber(tl:GetSetting("timelineFrameRate"))
local startFrame = tl:GetStartFrame()
local endFrame = tl:GetEndFrame()
local intervalFrames = math.floor(fps * INTERVAL_SECONDS)
local count = 0

for frame = startFrame, endFrame - 1, intervalFrames do
    local label = "Chapter " .. tostring(count + 1)
    tl:AddMarker(frame - startFrame, MARKER_COLOR, label, "", 1)
    count = count + 1
end

print("Added " .. count .. " markers every " .. INTERVAL_SECONDS .. " seconds.")
