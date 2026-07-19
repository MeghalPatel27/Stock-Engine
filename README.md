# Stock Intelligence Engine

**Status:** ADR-08 Backtesting **Finalized**. Paper harness runs on published real pilot data (no live serving yet).

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Labels](docs/labels/README.md)
- [Modeling](docs/decisions/07-modeling.md)
- [Backtesting](docs/decisions/08-backtesting.md) · [cost sources](docs/backtest/COST_SOURCES.md)
- [Feature backlog](docs/features/FEATURE_BACKLOG.md)
- [Pilot 5 stocks](docs/data/pilot_5_stocks/README.md)

## Current gate

Review pilot paper backtest, then **Inference / Serving ADR**.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite
uv run python research/experiments/run_walkforward_train.py --as-of YYYY-MM-DD --overwrite
uv run stock-engine-score --as-of YYYY-MM-DD
uv run stock-engine-backtest --as-of YYYY-MM-DD --out-dir data/backtests/run
uv run pytest
```

Backtests require **published** L1/features/labels for that as-of (real market CSVs → ingest). Cost defaults are cited in `docs/backtest/COST_SOURCES.md`.
