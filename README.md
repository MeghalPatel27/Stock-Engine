# Stock Intelligence Engine

**Status:** ADR-05 finalized. Feature **framework** ready for review. No concrete feature formulas yet.

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Feature registry notes](docs/features/)
- [Incoming CSV](docs/data/incoming.md)
- [Data dictionary](docs/data/dictionary/)
- [Data requirements vs public availability](docs/data/DATA_AVAILABILITY.md)
- [Pilot 5 stocks — CSV templates & sources](docs/data/pilot_5_stocks/README.md)

## Current gate

Review [`docs/decisions/05-feature-registry.md`](docs/decisions/05-feature-registry.md) implementation under `src/stock_engine/features/`.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run pytest
```
