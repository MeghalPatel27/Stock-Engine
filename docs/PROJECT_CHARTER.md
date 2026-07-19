# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** `raw__close_adj__l1` on `main`. Adding first computed feature `mom__ret__1d`.

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
| Feature — `raw__close_adj__l1` | ✅ |
| Feature — `mom__ret__1d` | ⏭️ in progress |
| More momentum / trend / vol / liq | ⛔ next |
| Labels → models → backtest → serve | ⛔ blocked |

## Hard stop

Do not implement RSI/MACD until a trivial **raw** feature has passed end-to-end through the framework.

## Next

1. Land `raw__close_adj__l1` E2E  
2. Simple return / rolling features by family  
3. Label Generation ADR
