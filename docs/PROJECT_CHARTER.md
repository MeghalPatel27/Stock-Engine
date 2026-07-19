# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** ADR-05 finalized. **Feature framework** implemented for review. No concrete feature formulas yet.

## Progress

| Step | Status |
|---|---|
| Charter / Philosophy | ✅ |
| Phase 1 Problem formulation | ✅ |
| Phase 0 Foundations | ✅ |
| Phase 2 Data acquisition | ✅ |
| Phase 3 Cleaning & normalization | ✅ APPROVED |
| ADR-05 Feature registry & store design | ✅ Finalized |
| **Feature framework** (registry / DAG / store / publisher) | ⏭️ **review** |
| Feature implementation (by family) | ⛔ blocked on framework review |
| Labels → models → backtest → serve | ⛔ blocked |

## Hard stop

Do not implement RSI/MACD/volatility/momentum formulas until the **feature framework** is reviewed.

## Give reviewers next

Framework package: `src/stock_engine/features/`  
ADR: `docs/decisions/05-feature-registry.md`  
Tests: `tests/unit/features/`
