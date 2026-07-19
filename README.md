# Stock Intelligence Engine

Daily post-close ranking of liquid Indian F&O equities by near-term cross-sectional outperformance probability.

**Status:** Phase 3 cleaning (L0/L1 + price-return CA adjustment) implemented. **Next gate: review cleaning, then Feature Registry design — not features/labels yet.**

## Source of truth

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Incoming CSV guide](docs/data/incoming.md)
- [Data dictionary](docs/data/dictionary/)

## Quickstart

```bash
uv sync --extra dev
uv run python scripts/bootstrap.py
# Drop equity_eod + corporate_actions + trading_calendar into data/incoming/
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run pytest
```

Clean outputs: `data/clean/l0/` (normalized) and `data/clean/l1/` (canonical — consume later).
