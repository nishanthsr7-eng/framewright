# Contributing

Bug reports, fixes and new servers are welcome. Keep changes small and focused: one server or one fix per PR.

## Setup

```bash
uv sync --all-packages        # every server into one workspace .venv
pre-commit install            # optional: ruff, ruff-format and pytest on commit
```

Needs `ffmpeg` and `ffprobe` on PATH. Models (`python scripts/fetch_models.py`) are only needed for subject_extractor and frame_extractor's upscaler.

## Before a PR

```bash
uv run --only-group dev ruff check .
uv run --only-group dev ruff format --check .
uv run --only-group test pytest              # add -m "not ffmpeg" to skip the ffmpeg integration tests
python scripts/run_evals.py                  # beat-sync + scenes; CI fails if these regress
python scripts/smoke_test.py <server>        # starts the server and lists its tools
```

Optional LLM eval (not in CI): copy `.env.example` to `.env`, fill in two hosted endpoints, then `uv run --group agent python evals/eval_agent.py`.

If you change dependencies, run `uv lock` and commit `uv.lock`.

## Adding a server

1. Pick a group: `servers/analysis/` (reads media, returns timings), `servers/assets/` (makes building blocks) or `servers/render/` (transforms video).
2. Copy a small server such as `servers/render/color_match/` and rename it:

   ```
   servers/<group>/<name>/
     pyproject.toml          name "<name>-mcp", console script "<name>-mcp", hatchling build
     README.md               one table: tool | key params | returns
     src/<name>_mcp/
       __init__.py
       server.py             MCP tool definitions only
       <logic>.py            the actual work, plain Python, testable without MCP
   ```

   Depend on `framewright-core` (workspace source) and `mcp[cli]`. The workspace picks up the new folder automatically.
3. Use the shared helpers in `framewright_core` instead of writing your own:
   - `run_ffmpeg(args, timeout=...)`, `probe_video(path)`, `video_codec_args(lossless)`
   - `default_output_path(input, suffix)`, `output_root()` (writes under `output/` at the repo root)
   - `setup_logging()`, `run_tool(fn, ...)` (maps `FileNotFoundError` / `ValueError` / `RuntimeError` to `ToolError`)
4. Register it in `.mcp.json.example`.

## Code rules

- **stdout is the MCP channel.** Never `print()` in server code; log to stderr with `logging`.
- **Tool parameters** have type hints and `Field(description=...)`. Use `Literal[...]` for fixed choices and `ge`/`le` bounds for numbers. Descriptions are short English.
- **Return a dict** with `output_path` plus the key metadata.
- **Bad input raises `ToolError`** with a hint on how to fix it ("File not found: x. Check the path exists.").
- **subprocess:** argument lists only, never `shell=True`, always a timeout.
- **Models:** support both footage styles (`style="anime" | "general"`) where a model is involved.
- **Video outputs** that other tools may chain should accept `lossless` (see [ADR 0004](docs/decisions/0004-lossless-intermediates.md)).
- Docs stay vendor-neutral: an example model name is fine, a required vendor is not.

## Tests

- Unit tests go in `tests/`. Keep pure logic (filters, plan math) in the logic module so it can be tested without MCP.
- Tests that call ffmpeg use `@pytest.mark.ffmpeg` and tiny `lavfi` inputs (a second or less, small frame sizes).
- Never commit media, models, `.mcp.json` or anything under `output/`.

## Design background

Why things are built the way they are: [docs/decisions/](docs/decisions/README.md).
