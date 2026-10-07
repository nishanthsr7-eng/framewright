# ADR 0002: One process per server

**Context.** Servers need heavy, clashing dependencies: torch, ONNX Runtime, faster-whisper (CTranslate2), librosa, OpenCV.

**Decision.** Each server is its own package with its own entry point and runs as its own MCP stdio process.

**Trade-off.**
- Dependency isolation: one server's pin can't break another. A crash stays in one process.
- Clients load only the servers they need.
- 19 processes when everything is enabled, each with its own cold start (model loads, imports).
- No shared in-memory cache: two servers that need the same decoded audio each decode it.
