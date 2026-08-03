<#
.SYNOPSIS
  Install Framewright's Lua scripts and Fusion templates into DaVinci Resolve.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File resolve\install.ps1
  powershell -ExecutionPolicy Bypass -File resolve\install.ps1 -Uninstall
  powershell -ExecutionPolicy Bypass -File resolve\install.ps1 -DryRun
  powershell -ExecutionPolicy Bypass -File resolve\install.ps1 -Dest "D:\Custom\Fusion"
#>
param(
    [switch]$Uninstall,  # remove only the files this repo installs
    [switch]$DryRun,     # print actions, change nothing
    [string]$Dest = ""   # Fusion folder; default is Resolve's per-user folder
)
$ErrorActionPreference = "Stop"

$src = $PSScriptRoot
if (-not $Dest) {
    $Dest = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion"
}

# source folder -> target folder under the Fusion folder
$map = @(
    @{ From = "scripts\Edit";          To = "Scripts\Edit" },
    @{ From = "scripts\Utility";       To = "Scripts\Utility" },
    @{ From = "templates\Titles";      To = "Templates\Edit\Titles" },
    @{ From = "templates\Effects";     To = "Templates\Edit\Effects" },
    @{ From = "templates\Transitions"; To = "Templates\Edit\Transitions" },
    @{ From = "templates\Generators";  To = "Templates\Edit\Generators" }
)

if (-not (Test-Path $Dest) -and -not $Uninstall) {
    Write-Host "Fusion folder not found: $Dest"
    Write-Host "Start DaVinci Resolve once so it creates the folder, or pass -Dest <path>."
    exit 1
}

$mode = if ($Uninstall) { "Removing" } else { "Installing" }
if ($DryRun) { $mode = "[dry run] $mode" }
Write-Host "$mode -> $Dest"

$count = 0
foreach ($m in $map) {
    $from = Join-Path $src $m.From
    $to = Join-Path $Dest $m.To
    if (-not (Test-Path $from)) { continue }
    if (-not $Uninstall -and -not $DryRun) { New-Item -ItemType Directory -Force -Path $to | Out-Null }
    foreach ($f in Get-ChildItem -Path $from -File) {
        $target = Join-Path $to $f.Name
        if ($Uninstall) {
            if (Test-Path $target) {
                if (-not $DryRun) { Remove-Item -LiteralPath $target -Force }
                $count++
            }
        } else {
            if (-not $DryRun) { Copy-Item -LiteralPath $f.FullName -Destination $target -Force }
            $count++
        }
    }
}

# Framewright_Build_Plan.lua can't read env vars or files in Resolve's sandbox: bake in the repo path.
$fw = Join-Path $Dest "Scripts\Edit\Framewright_Build_Plan.lua"
if (-not $Uninstall -and -not $DryRun -and (Test-Path $fw)) {
    $root = (Split-Path $src -Parent) -replace "\\", "/"
    $text = [IO.File]::ReadAllText($fw).Replace("__FRAMEWRIGHT_ROOT__", $root)
    [IO.File]::WriteAllText($fw, $text, (New-Object Text.UTF8Encoding $false))  # no BOM: Lua rejects it
}

$verb = if ($Uninstall) { "removed" } else { "installed" }
if ($DryRun) { $verb = "would be $verb" }
Write-Host "$count files $verb."
if (-not $Uninstall) { Write-Host "Restart DaVinci Resolve to see them (Workspace > Scripts, Effects panel)." }
