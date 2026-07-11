-- Removes every marker from the current timeline.
-- Prints a count of how many were removed.

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local markers = timeline:GetMarkers()
if not markers or not next(markers) then
    print("No markers found. Nothing to remove.")
    return
end

local count = 0
for frame, _ in pairs(markers) do
    timeline:DeleteMarkerAtFrame(frame)
    count = count + 1
end

print(string.format("Removed %d marker(s) from timeline '%s'.", count, timeline:GetName()))
