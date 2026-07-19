# Stock Intelligence Engine

**Status:** ADR-05 feature **framework approved**. Next after merge: first raw projection feature (not RSI/MACD).

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Feature registry notes](docs/features/)
- [Incoming CSV](docs/data/incoming.md)
- [Data dictionary](docs/data/dictionary/)
- [Data requirements vs public availability](docs/data/DATA_AVAILABILITY.md)
- [Pilot 5 stocks — CSV templates & sources](docs/data/pilot_5_stocks/README.md)

## Current gate

Merge the feature framework PR, then add the first `feature_type: raw` projection.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-lint-features
uv run pytest
```
