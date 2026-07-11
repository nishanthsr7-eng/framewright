-- Exports a full clip list with timecodes to Desktop as clip_list.txt
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
tl = proj:GetCurrentTimeline()

if not tl then print("No active timeline."); return end

local fps = tonumber(tl:GetSetting("timelineFrameRate"))
local outPath = os.getenv("USERPROFILE") .. "\\Desktop\\clip_list.txt"
local file = io.open(outPath, "w")

if not file then
    print("ERROR: Cannot write to Desktop. Check permissions.")
    return
end

local function toTC(frame)
    local h = math.floor(frame / (fps * 3600))
    local m = math.floor((frame % (fps * 3600)) / (fps * 60))
    local s = math.floor((frame % (fps * 60)) / fps)
    local f = math.floor(frame % fps)
    return string.format("%02d:%02d:%02d:%02d", h, m, s, f)
end

file:write("CLIP LIST  |  " .. tl:GetName() .. "\n")
file:write(string.rep("=", 72) .. "\n\n")

local vTracks = tl:GetTrackCount("video")
for track = 1, vTracks do
    local items = tl:GetItemListInTrack("video", track)
    if items and #items > 0 then
        file:write("VIDEO TRACK " .. track .. "\n")
        file:write(string.rep("-", 72) .. "\n")
        for i, item in ipairs(items) do
            local name = item:GetName()
            local startTC = toTC(item:GetStart())
            local endTC   = toTC(item:GetEnd())
            local durTC   = toTC(item:GetEnd() - item:GetStart())
            file:write(string.format("  %3d.  %-35s  IN: %s  DUR: %s\n", i, name, startTC, durTC))
        end
        file:write("\n")
    end
end

file:close()
print("Exported to: " .. outPath)
