#!/usr/bin/env bash
# Framewright setup (Linux/macOS): install every server, fetch models, run the smoke test.
# Usage: scripts/setup.sh [--skip-models] [--skip-smoke]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_MODELS=0; SKIP_SMOKE=0
for arg in "$@"; do
  case "$arg" in
    --skip-models) SKIP_MODELS=1 ;;
    --skip-smoke) SKIP_SMOKE=1 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

for cmd in uv ffmpeg ffprobe; do
  command -v "$cmd" >/dev/null || { echo "$cmd not found on PATH. Install it first (see docs/setup.md)." >&2; exit 1; }
done

# One workspace, one lockfile: install every server into the root .venv.
echo "[sync] all servers"
uv sync --quiet --all-packages --directory "$ROOT" || { echo "uv sync failed (see above)." >&2; exit 1; }

if [ "$SKIP_MODELS" -eq 0 ]; then
  uv run --no-project python "$ROOT/scripts/fetch_models.py" || { echo "Model download failed. Retry: python scripts/fetch_models.py" >&2; exit 1; }
fi

if [ ! -f "$ROOT/.mcp.json" ]; then
  cp "$ROOT/.mcp.json.example" "$ROOT/.mcp.json"
  echo "Created .mcp.json from .mcp.json.example"
fi

if [ "$SKIP_SMOKE" -eq 0 ]; then
  uv run --no-project python "$ROOT/scripts/smoke_test.py" || { echo "Smoke test failed (see above)." >&2; exit 1; }
fi
echo "Setup complete."
