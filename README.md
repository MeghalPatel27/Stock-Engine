# Stock Intelligence Engine

Daily post-close ranking of liquid Indian F&O equities by near-term cross-sectional outperformance probability.

**Status:** Phase 2 ingestion foundation on `main` (local CSV only). No features/labels/models yet. Next: architecture review, then Phase 3+ design.

## Source of truth

- [Project charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Incoming CSV guide](docs/data/incoming.md)

## Dev quickstart

```bash
uv sync --extra dev
uv run python scripts/bootstrap.py
# Drop equity_eod.csv + corporate_actions.csv into data/incoming/
uv run stock-engine-ingest
uv run pytest
uv run ruff check src tests scripts
```
