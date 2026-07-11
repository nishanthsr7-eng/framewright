-- Sorts all clips in the root bin into Video / Audio / Images / Other sub-bins.
-- Run from Workspace > Scripts > Utility

resolve = Resolve()
pm = resolve:GetProjectManager()
proj = pm:GetCurrentProject()
mp = proj:GetMediaPool()

if not mp then print("Cannot access Media Pool."); return end

local root = mp:GetRootFolder()
local clips = root:GetClipList()

if not clips or #clips == 0 then
    print("No clips in root bin to organize.")
    return
end

local VIDEO_EXT  = { mp4=1, mov=1, mxf=1, avi=1, mkv=1, r3d=1, braw=1, dng=1, mts=1, m2ts=1 }
local AUDIO_EXT  = { mp3=1, wav=1, aiff=1, aif=1, aac=1, flac=1, ogg=1, m4a=1 }
local IMAGE_EXT  = { png=1, jpg=1, jpeg=1, tif=1, tiff=1, psd=1, exr=1, dpx=1, bmp=1 }

local bins = {}
local function getBin(name)
    if not bins[name] then
        bins[name] = mp:AddSubFolder(root, name)
    end
    return bins[name]
end

local moved = 0
for _, clip in ipairs(clips) do
    local props = clip:GetClipProperty()
    if props then
        local path = props["File Path"] or ""
        local ext = path:match("%.(%w+)$")
        if ext then
            ext = ext:lower()
            local binName
            if VIDEO_EXT[ext] then binName = "Video"
            elseif AUDIO_EXT[ext] then binName = "Audio"
            elseif IMAGE_EXT[ext] then binName = "Images"
            else binName = "Other"
            end
            mp:MoveClips({clip}, getBin(binName))
            moved = moved + 1
        end
    end
end

print("Organized " .. moved .. " clips into bins: Video / Audio / Images / Other")
