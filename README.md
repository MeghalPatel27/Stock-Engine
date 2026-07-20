# Stock Intelligence Engine

**Status:** ADR-09 Inference **Finalized**. Daily `stock-engine-infer` publishes RankRows locally (no brokers).

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Labels](docs/labels/README.md)
- [Modeling](docs/decisions/07-modeling.md)
- [Backtesting](docs/decisions/08-backtesting.md) · [cost sources](docs/backtest/COST_SOURCES.md)
- [Inference](docs/inference/README.md)
- [Feature backlog](docs/features/FEATURE_BACKLOG.md)
- [Pilot 5 stocks](docs/data/pilot_5_stocks/README.md)

## Current gate

Review daily infer publish. No live broker integration yet.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite
uv run python research/experiments/run_walkforward_train.py --as-of YYYY-MM-DD --overwrite
uv run stock-engine-infer --as-of YYYY-MM-DD --overwrite
uv run stock-engine-backtest --as-of YYYY-MM-DD --out-dir data/backtests/run
uv run pytest
```

Inference requires published features + a frozen model. Labels are train/eval only.
