# ADR 0001: The LLM writes a Lua script instead of driving Resolve live

**Context.** DaVinci Resolve Free has no external scripting API: an outside process cannot connect to it. Resolve 21.1 also runs Lua in a sandbox (no `io`, no Python scripts, only the `resolve` global).

**Decision.** The LLM writes a Lua script that uses `resolve/bridge/` helpers. The editor runs it from Resolve's Workspace > Scripts menu.

**Trade-off.**
- Works on the Free edition, and every change is a plain file you can read and audit before it runs.
- The script is re-runnable and can live in version control.
- No live feedback loop: the LLM can't inspect the timeline after each step. Errors show up in `ResolveDebug.txt`, not in the chat.
- The script must fit the sandbox, so file I/O happens on the MCP side.
