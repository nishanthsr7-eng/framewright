# ADR 0004: Lossless qp-0 intermediates

**Context.** File handoff (ADR 0003) means a clip can pass through several render servers. Each lossy re-encode adds generation loss, which shows up as banding and smeared edges by the third or fourth step.

**Decision.** Render servers can write intermediates as lossless H.264 (`lossless=True`, i.e. `-qp 0`). Only the final export uses a lossy delivery preset.

**Trade-off.**
- Quality stays the same however many steps are chained.
- Files are much larger, often 10x or more, and some players handle qp-0 poorly.
- The final export is still lossy, so the loss happens once instead of once per step.
