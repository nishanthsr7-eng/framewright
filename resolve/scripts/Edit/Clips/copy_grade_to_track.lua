-- Prints all clip names on a chosen track so you can use Resolve's built-in
-- grade copy tools (Alt+G to grab grade, Alt+drag to apply) efficiently.
-- Also marks the first clip Green as the "source" grade clip.

local SOURCE_TRACK = 1   -- track containing the graded reference clip

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local items = timeline:GetItemListInTrack("video", SOURCE_TRACK)
if not items or #items == 0 then
    print(string.format("No clips on V%d.", SOURCE_TRACK))
    return
end

print("=== COPY GRADE HELPER ===")
print(string.format("Track V%d has %d clips.", SOURCE_TRACK, #items))
print("")
print("STEP 1: Click the clip whose grade you want to copy.")
print("STEP 2: In the Color page, right-click its thumbnail -> Grab Still.")
print("STEP 3: In the Gallery, drag the still onto any other clip to apply the grade.")
print("")
print("--- OR use keyboard shortcuts on the Color page ---")
print("  Ctrl+C  = Copy grade from selected clip")
print("  Ctrl+V  = Paste grade to selected clip")
print("  Alt+drag thumbnail in timeline = apply grade to target clip")
print("")

-- Mark the first clip as source reference
items[1]:SetClipColor("Green")
print(string.format("Marked first clip '%s' in Green as your grade source.", items[1]:GetName()))
print("")
print("All clips on V" .. SOURCE_TRACK .. ":")
for i, item in ipairs(items) do
    print(string.format("  %2d. %s  (%d frames)", i, item:GetName(), item:GetEnd() - item:GetStart()))
end
