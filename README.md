# Stock Intelligence Engine

Daily post-close ranking of liquid Indian F&O equities by near-term cross-sectional outperformance probability.

**Status:** Ingest foundation approved. **Phase 3 cleaning/CA design awaiting sign-off.** No features/labels/models.

## Source of truth

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Incoming CSV guide](docs/data/incoming.md)

## Current gate

Sign off **[`docs/decisions/04-phase3-proposal.md`](docs/decisions/04-phase3-proposal.md)**

## Dev quickstart

```bash
uv sync --extra dev
uv run python scripts/bootstrap.py
# Drop CSVs into data/incoming/ — see docs/data/incoming.md
uv run stock-engine-ingest
uv run pytest
```
