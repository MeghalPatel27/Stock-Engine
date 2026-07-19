# Stock Intelligence Engine

Daily post-close ranking of liquid Indian F&O equities by near-term cross-sectional outperformance probability.

**Status:** Phase 0 scaffolded. Phase 1 + Phase 0 ADRs finalized. **Phase 2 data-acquisition design awaiting sign-off** — no ingestion implementation yet.

## Source of truth

- [Project charter](docs/PROJECT_CHARTER.md)
- [Decision records (ADRs)](docs/decisions/)

## Current gate

Sign off **Phase 2**: [`docs/decisions/03-phase2-proposal.md`](docs/decisions/03-phase2-proposal.md)

## Dev quickstart (local)

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests scripts
uv run python scripts/bootstrap.py
```
