# Backtesting

See [ADR-08](../decisions/08-backtesting.md) and [COST_SOURCES.md](COST_SOURCES.md).

## Requirements

Published **real** partitions only:

- `data/clean/l1/equity_eod/as_of_date=…`
- `data/features/core/v1/as_of_date=…`
- `data/labels/core/v1/horizon=5/as_of_date=…`

No synthetic market panels are accepted by the harness.

## Run

```bash
uv run stock-engine-backtest --as-of 2026-07-17 --out-dir data/backtests/pilot_2026-07-17
```

## Pilot run (workspace, as-of 2026-07-17)

Data: 5 NSE F&O names (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK), 1233 sessions (2021-07-20 → 2026-07-10 labeled), published L1/features/labels.

| Metric | Value |
|---|---|
| Folds used | 46 |
| Decision periods | 230 |
| Trades | 790 |
| Mean gross period return | ~+0.03% |
| Mean cost fraction | ~0.33% (STT/stamp/exchange/SEBI/GST/DP + 5 bps slip) |
| Net CAGR | negative on this 5-name pilot |
| Note | Pilot metrics are **not** production benchmarks |

Costs use the statutory/exchange defaults in `COST_SOURCES.md`.
