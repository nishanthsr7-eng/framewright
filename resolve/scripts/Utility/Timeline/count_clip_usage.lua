-- Counts how many times each clip name appears on the timeline (all video tracks).
-- Useful for finding overused or unused media.

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local trackCount = timeline:GetTrackCount("video")
local usage = {}

for t = 1, trackCount do
    local items = timeline:GetItemListInTrack("video", t)
    if items then
        for _, item in ipairs(items) do
            local name = item:GetName() or "(unnamed)"
            usage[name] = (usage[name] or 0) + 1
        end
    end
end

-- Sort by usage count descending
local sorted = {}
for name, count in pairs(usage) do
    table.insert(sorted, { name = name, count = count })
end
table.sort(sorted, function(a, b) return a.count > b.count end)

print("=== CLIP USAGE COUNT ===")
print(string.format("%-50s  %s", "Clip Name", "Uses"))
print(string.rep("-", 58))
for _, entry in ipairs(sorted) do
    print(string.format("%-50s  %d", entry.name:sub(1, 50), entry.count))
end
print(string.rep("-", 58))
print("Total unique clips: " .. #sorted)
