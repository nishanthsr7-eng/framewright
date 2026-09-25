# Framewright setup (Windows): install every server, fetch models, run the smoke test.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-SkipModels] [-SkipSmoke]
param([switch]$SkipModels, [switch]$SkipSmoke)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

foreach ($cmd in "uv", "ffmpeg", "ffprobe") {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "$cmd not found on PATH. Install it first (see docs/setup.md)."
    }
}

# One workspace, one lockfile: install every server into the root .venv.
Write-Host "[sync] all servers"
uv sync --quiet --all-packages --directory $Root
if ($LASTEXITCODE -ne 0) { Write-Error "uv sync failed (see above)." }

if (-not $SkipModels) {
    uv run --no-project python "$Root\scripts\fetch_models.py"
    if ($LASTEXITCODE -ne 0) { Write-Error "Model download failed. Retry: python scripts\fetch_models.py" }
}

if (-not (Test-Path "$Root\.mcp.json")) {
    Copy-Item "$Root\.mcp.json.example" "$Root\.mcp.json"
    Write-Host "Created .mcp.json from .mcp.json.example"
}

if (-not $SkipSmoke) {
    uv run --no-project python "$Root\scripts\smoke_test.py"
    if ($LASTEXITCODE -ne 0) { Write-Error "Smoke test failed (see above)." }
}
Write-Host "Setup complete."
