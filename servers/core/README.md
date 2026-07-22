# framewright-core

Shared helpers used by every Framewright server. Not an MCP server itself.

| Helper | What it does |
|---|---|
| `servers_dir()` / `output_root()` | find `servers/` by walking up; default output is `<repo>/output` |
| `run_ffmpeg(args, timeout, cwd)` | run `ffmpeg -y ...`, raise `RuntimeError` with the stderr tail on failure, return stderr |
| `run_tool(fn, ...)` | call tool logic and turn errors into `ToolError` with a fix hint |
| `setup_logging()` | log to stderr (stdout is the MCP channel) |
