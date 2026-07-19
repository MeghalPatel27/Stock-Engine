# Stock Intelligence Engine

**Status:** ADR-07 Modeling **Finalized**. Implementing PICK A (no backtest/serving yet).

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Labels](docs/labels/README.md)
- [Modeling](docs/decisions/07-modeling.md)
- [Feature backlog](docs/features/FEATURE_BACKLOG.md)
- [Pilot 5 stocks](docs/data/pilot_5_stocks/README.md)

## Current gate

Land Modeling **PICK A**, then Backtesting ADR.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite
uv run python research/experiments/run_walkforward_train.py --as-of YYYY-MM-DD --overwrite
uv run stock-engine-score --as-of YYYY-MM-DD
uv run pytest
```
