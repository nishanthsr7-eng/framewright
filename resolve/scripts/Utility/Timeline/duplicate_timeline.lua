-- Creates a duplicate of the current timeline named "<original> COPY".
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
mp = proj:GetMediaPool()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local originalName = tl:GetName()
local copyName = originalName .. " COPY"

local newTL = mp:DuplicateTimeline(tl)
if newTL then
    newTL:SetName(copyName)
    print("Created: " .. copyName)
else
    print("ERROR: Could not duplicate timeline.")
end
