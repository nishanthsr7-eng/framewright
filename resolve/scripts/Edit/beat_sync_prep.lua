-- Reads all timeline markers and prints frame positions for beat-sync reference.
-- Also prints a copy-paste friendly list of edit points (clip start frames) on V1.
-- Use this output to line up your cuts with music beats manually or in a spreadsheet.

local resolve = Resolve()
local pm = resolve:GetProjectManager()
local project = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline is open.")
    return
end

local fps = tonumber(timeline:GetSetting("timelineFrameRate"))
local startTC = timeline:GetStartFrame()

local function framesToTC(f)
    local totalSec = math.floor(f / fps)
    local fr = f % fps
    local s  = totalSec % 60
    local m  = math.floor(totalSec / 60) % 60
    local h  = math.floor(totalSec / 3600)
    return string.format("%02d:%02d:%02d:%02d", h, m, s, fr)
end

print("=== BEAT SYNC PREP ===")
print("Timeline: " .. timeline:GetName())
print(string.format("Frame rate: %.2f fps", fps))
print("")

-- Print all markers (these are your beat markers if you placed them with add_interval_markers)
local markers = timeline:GetMarkers()
if markers and next(markers) then
    print("--- MARKERS (beat reference points) ---")
    local sortedFrames = {}
    for frame, _ in pairs(markers) do
        table.insert(sortedFrames, frame)
    end
    table.sort(sortedFrames)
    for _, frame in ipairs(sortedFrames) do
        local m = markers[frame]
        print(string.format("  Frame %5d  |  %s  |  %s  |  %s",
            frame + startTC,
            framesToTC(frame),
            m.color or "?",
            m.name or ""))
    end
    print("")
else
    print("No markers found. Run add_interval_markers first to add beat markers.")
    print("")
end

-- Print all V1 clip edit points
print("--- V1 CLIP EDIT POINTS ---")
local trackCount = timeline:GetTrackCount("video")
if trackCount >= 1 then
    local items = timeline:GetItemListInTrack("video", 1)
    if items then
        for i, item in ipairs(items) do
            local s = item:GetStart()
            local e = item:GetEnd()
            local name = item:GetName() or "clip"
            print(string.format("  Clip %3d  |  Start: %s (f%d)  |  End: %s (f%d)  |  %s",
                i,
                framesToTC(s - startTC), s,
                framesToTC(e - startTC), e,
                name))
        end
    else
        print("  (no clips on V1)")
    end
else
    print("  (no video tracks)")
end

print("")
print("=== TIP: Add markers at each music beat using Edit > Add Marker, then compare frame numbers above to line up cuts. ===")
