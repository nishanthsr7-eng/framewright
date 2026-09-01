-- Inserts 2 white frames at the playhead position using a white generator clip
local FLASH_FRAMES = 2

local resolve = Resolve()
local pm = resolve:GetProjectManager()
local project = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local playhead = timeline:GetCurrentVideoItem()
if not playhead then
    print("INFO: Place the playhead on a clip to insert flash before it.")
    return
end

local fps = tonumber(timeline:GetSetting("timelineFrameRate"))
local startFrame = playhead:GetStart()

-- Add a bright white color marker at the cut point as a visual indicator
-- (True clip insertion requires drag-and-drop from a generator; markers are the scripting workaround)
local markerAdded = timeline:AddMarker(startFrame, "White", "FLASH HERE", "Insert " .. FLASH_FRAMES .. " white frames at this cut", 1)

if markerAdded then
    print("Flash marker added at frame " .. startFrame .. ".")
    print("MANUAL STEP: In the timeline, right-click the white marker → place a 'Color' generator (white) of " .. FLASH_FRAMES .. " frame(s) at this point.")
    print("TIP: Use Effects → Toolbox → Generators → Color, drag to V2, trim to " .. FLASH_FRAMES .. " frame(s).")
else
    print("Could not add marker. Make sure a timeline is open and the playhead is on a clip.")
end
