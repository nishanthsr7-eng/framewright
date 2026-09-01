-- Adds Cyan markers at the start of every clip on V1 as a reminder to apply an effect.
-- Since Resolve's free API cannot drag-drop effects programmatically, this creates
-- a visible guide: each Cyan marker = one clip that needs the effect applied manually.

local EFFECT_NAME = "Chromatic Aberration"  -- change to remind yourself which effect to add
local TRACK       = 1

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local startTC = timeline:GetStartFrame()
local items   = timeline:GetItemListInTrack("video", TRACK)

if not items then
    print(string.format("No clips on V%d.", TRACK))
    return
end

local added = 0
for i, item in ipairs(items) do
    local frame = item:GetStart() - startTC
    local note  = "Apply: " .. EFFECT_NAME
    timeline:AddMarker(frame, "Cyan", "FX " .. i, note, 1)
    added = added + 1
end

print(string.format("Added %d Cyan markers on V%d.", added, TRACK))
print("HOW TO APPLY EFFECT:")
print("  1. Go to Effects -> Fusion Effects in the Effects panel")
print('  2. Find "' .. EFFECT_NAME .. '"')
print("  3. Drag it onto each marked clip")
print("  4. Run remove_all_markers when done to clean up")
