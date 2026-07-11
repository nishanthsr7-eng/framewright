-- Exports every timeline marker to a CSV file on the Desktop.
-- Columns: Frame, Timecode, Color, Name, Note, Duration

local resolve  = Resolve()
local pm       = resolve:GetProjectManager()
local project  = pm:GetCurrentProject()
local timeline = project:GetCurrentTimeline()

if not timeline then
    print("ERROR: No timeline open.")
    return
end

local fps     = tonumber(timeline:GetSetting("timelineFrameRate"))
local startTC = timeline:GetStartFrame()
local markers = timeline:GetMarkers()

if not markers or not next(markers) then
    print("No markers found in this timeline.")
    return
end

local function framesToTC(f)
    local totalSec = math.floor(f / fps)
    local fr = f % fps
    local s  = totalSec % 60
    local m  = math.floor(totalSec / 60) % 60
    local h  = math.floor(totalSec / 3600)
    return string.format("%02d:%02d:%02d:%02d", h, m, s, fr)
end

local desktopPath = os.getenv("USERPROFILE") .. "\\Desktop\\markers_export.csv"
local f = io.open(desktopPath, "w")
if not f then
    print("ERROR: Could not write to Desktop. Check permissions.")
    return
end

f:write("Frame,Timecode,Color,Name,Note,Duration\n")

local sortedFrames = {}
for frame in pairs(markers) do table.insert(sortedFrames, frame) end
table.sort(sortedFrames)

for _, frame in ipairs(sortedFrames) do
    local m    = markers[frame]
    local absF = frame + startTC
    local tc   = framesToTC(frame)
    local name  = (m.name  or ""):gsub('"', '""')
    local note  = (m.note  or ""):gsub('"', '""')
    local color = m.color or ""
    local dur   = m.duration or 1
    f:write(string.format('%d,"%s","%s","%s","%s",%d\n',
        absF, tc, color, name, note, dur))
end

f:close()
print("Exported " .. #sortedFrames .. " markers to: " .. desktopPath)
