-- Scans all V1 clips and flags those that DON'T match the target duration.
-- Clips that match get Green; clips that don't match get Orange.
-- Great for beat edits where every clip should be the same length.

local TARGET_FRAMES = 24   -- change this to your desired clip length in frames

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local items = timeline:GetItemListInTrack("video", 1)
if not items then
    print("No clips on V1.")
    return
end

local matched   = 0
local different = 0

print(string.format("=== DURATION CHECK (target: %d frames) ===", TARGET_FRAMES))

for i, item in ipairs(items) do
    local len  = item:GetEnd() - item:GetStart()
    local name = item:GetName() or "(unnamed)"
    if len == TARGET_FRAMES then
        item:SetClipColor("Green")
        matched = matched + 1
    else
        item:SetClipColor("Orange")
        different = different + 1
        print(string.format("  MISMATCH Clip %d: '%s' — %d frames (expected %d)",
            i, name, len, TARGET_FRAMES))
    end
end

print(string.format("\nResult: %d match (Green), %d differ (Orange).", matched, different))
print("TIP: Trim the Orange clips in the timeline to match the target length.")
