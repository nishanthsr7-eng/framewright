"""Start every MCP server and list its tools.

Usage:
    python scripts/smoke_test.py                     # all servers
    python scripts/smoke_test.py effects chroma_key  # pick some

Exits non-zero if any server fails to start or reports no tools.
Stdlib only (Python 3.10+).
"""

from __future__ import annotations

import json
import queue
import re
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVERS = ROOT / "servers"
TIMEOUT = 180  # first run may build the venv


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _script_name(pyproject: Path) -> str | None:
    text = pyproject.read_text(encoding="utf-8")
    block = re.search(r"^\[project\.scripts\]\s*\n(.*?)(?:^\[|\Z)", text, re.M | re.S)
    if not block:
        return None
    m = re.search(r"^\s*([\w.-]+)\s*=", block.group(1), re.M)
    return m.group(1) if m else None


def _rpc(proc: subprocess.Popen, lines: queue.Queue, msg: dict) -> dict | None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()
    if "id" not in msg:
        return None
    while True:
        line = lines.get(timeout=TIMEOUT)
        if line is None:
            raise RuntimeError("server exited")
        try:
            reply = json.loads(line)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"non-JSON on stdout: {line[:120]!r}") from e
        if reply.get("id") == msg["id"]:
            if "error" in reply:
                raise RuntimeError(reply["error"].get("message", "error"))
            return reply["result"]


def check(server_dir: Path) -> tuple[bool, str]:
    script = _script_name(server_dir / "pyproject.toml")
    if not script:
        return False, "no [project.scripts] entry"
    proc = subprocess.Popen(
        ["uv", "run", "--quiet", "--directory", str(server_dir), script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    lines: queue.Queue = queue.Queue()
    err: list[str] = []

    def pump(stream, sink):
        for line in stream:
            sink(line.strip())
        if stream is proc.stdout:
            lines.put(None)

    threading.Thread(target=pump, args=(proc.stdout, lines.put), daemon=True).start()
    threading.Thread(target=pump, args=(proc.stderr, err.append), daemon=True).start()
    try:
        _rpc(
            proc,
            lines,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "framewright-smoke", "version": "1"},
                },
            },
        )
        _rpc(proc, lines, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        listing = _rpc(proc, lines, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = listing["tools"] if listing else []
        if not tools:
            return False, "no tools"
        return True, ", ".join(t["name"] for t in tools)
    except queue.Empty:
        return False, f"timed out after {TIMEOUT}s"
    except RuntimeError as e:
        tail = err[-1] if err else ""
        return False, f"{e}{' | ' + tail if tail else ''}"
    finally:
        proc.kill()
        proc.wait(timeout=10)


def main() -> int:
    wanted = set(sys.argv[1:])
    dirs = sorted(p.parent for p in SERVERS.glob("*/*/pyproject.toml"))
    if wanted:
        dirs = [d for d in dirs if d.name in wanted]
        missing = wanted - {d.name for d in dirs}
        if missing:
            _log(f"unknown server(s): {', '.join(sorted(missing))}")
            return 2
    failed = []
    for d in dirs:
        ok, info = check(d)
        _log(f"[{'ok' if ok else 'FAIL':4s}] {d.parent.name}/{d.name}: {info}")
        if not ok:
            failed.append(d.name)
    _log(f"\n{len(dirs) - len(failed)}/{len(dirs)} servers OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
