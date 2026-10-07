# ADR 0003: File handoff via `output/` instead of in-memory

**Context.** Steps chain across separate processes (ADR 0002) and finish in Resolve, which only reads files.

**Decision.** Every tool writes its result to `output/` and returns `output_path`. The next tool takes that path as input.

**Trade-off.**
- Every intermediate can be opened, checked and re-used. Any step can be re-run alone.
- Works across processes and with Resolve with no extra plumbing.
- Costs disk space, and each video step decodes and re-encodes (see ADR 0004).
- Users must clean `output/` now and then.
