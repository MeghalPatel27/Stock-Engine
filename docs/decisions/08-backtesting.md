# ADR 08 — Backtesting

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Depends on:** [01-phase1.md](01-phase1.md), [06-label-generation.md](06-label-generation.md), [07-modeling.md](07-modeling.md)

## Sign-off locks

1. Backtests consume **only published** L1 / features / labels / model artifacts — never synthetic market panels.  
2. Trading-cost defaults are taken from **NSE / statutory schedules** (cited below), not invented.  
3. Evaluation is **purged expanding walk-forward** aligned with ADR-07 (no in-sample paper PnL).  
4. Pilot universe metrics are **not** production benchmarks (same warning as labels).

## Locked decisions

| Topic | Decision |
|---|---|
| Signal time | Session close `T` (post-close ranks) |
| Fill model | Enter / exit at **next open** after decision (`T+1` open); exit after `H` sessions at open of `T+1+H` |
| Horizon | H=5 (V1) |
| Portfolio | Equal-weight Top-K longs + equal-weight Top-K shorts (dollar-neutral book) |
| K | `min(top_n, floor(n_eligible/2))` — on 5-name pilot, K=1 |
| Costs | India equity **delivery** schedule (see §Costs) |
| Slippage | Configurable one-way bps; default **5 bps** for liquid large-caps (assumption; not a statutory rate) |
| Metrics | Net CAGR, vol, Sharpe (rf=0), max DD, turnover, hit-rate, avg cost bps |
| Data | Fail-closed if published partitions missing |

## Costs (verified sources)

Equity **delivery** cash segment (NSE), defaults in `config/default.yaml` → `backtest.costs`:

| Component | Default | Side | Source |
|---|---|---|---|
| STT | **0.10%** | Buy and sell | [NSE — STT & levies](https://www.nseindia.com/static/invest/first-time-investor-sebi-turnover-fees-stt-other-levies) (delivery equity share 0.100%) |
| Stamp duty | **0.015%** | Buy only | [NSE — Stamp duty](https://www.nseindia.com/static/invest/first-time-investor-stamp-duty-charges-taxes) (delivery, buyer) |
| NSE txn charge | **0.00297%** | Each side | NSE cash equity schedule (FY 2025–26), as published via exchange member circulars / broker pass-through tables |
| SEBI turnover fee | **₹10 / crore** (= 0.0001%) | Each side | NSE SEBI turnover fee schedule |
| GST | **18%** | On brokerage + exchange + SEBI (not STT/stamp) | GST Act (India) |
| Brokerage | **0%** | — | Discount-broker delivery default (e.g. Zerodha equity delivery ₹0); override in config |
| DP charges | **₹15.34 / sell scrip** | Sell | Depository participant charge (broker tariff; Zerodha-published ₹13.5+GST ≈ ₹15.34) — optional toggle |
| Slippage | **5 bps** one-way | Each side | Modeling assumption for liquid F&O large-caps (not statutory) |

Round-trip variable statutory+exchange drag (0 brokerage, ignore flat DP):  
≈ STT 0.20% + stamp 0.015% + 2×txn + 2×SEBI + GST on txn/SEBI ≈ **0.22%** before slippage.

## Pipeline

```text
published features ⋈ labels ⋈ L1 prices
  → purged expanding WF scores (ADR-07)
  → Top-K L/S books each decision day in test folds
  → open-to-open H-day gross return
  → subtract delivery cost model
  → aggregate net metrics + trade blotter
```

## Explicit non-goals

No live orders. No intraday. No options/futures cost schedule. No full tax (STCG/LTCG) modeling.

## First implementation

Harness + CLI + config + run on **pilot published** `as_of=2026-07-17` data already in the repo workspace.
