# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** Feature framework on `main`. Implementing first raw feature (`raw__close_adj__l1`).

## Progress

| Step | Status |
|---|---|
| Charter / Philosophy | ✅ |
| Phase 1 Problem formulation | ✅ |
| Phase 0 Foundations | ✅ |
| Phase 2 Data acquisition | ✅ |
| Phase 3 Cleaning & normalization | ✅ APPROVED |
| ADR-05 Feature registry & store design | ✅ Finalized |
| **Feature framework** (registry / DAG / store / publisher) | ✅ APPROVED (+ follow-ups) |
| Feature implementation — `raw__close_adj__l1` | ⏭️ in progress |
| Feature families (returns / trend / vol / liq) | ⛔ after first raw E2E |
| Labels → models → backtest → serve | ⛔ blocked |

## Hard stop

Do not implement RSI/MACD until a trivial **raw** feature has passed end-to-end through the framework.

## Next

1. Land `raw__close_adj__l1` E2E  
2. Simple return / rolling features by family  
3. Label Generation ADR
