# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** ADR-05 framework **APPROVED** (with follow-ups implemented). Next: first raw projection feature after merge.

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
| Feature implementation (raw projection first, then families) | ⏭️ after PR merge |
| Labels → models → backtest → serve | ⛔ blocked |

## Hard stop

Do not implement RSI/MACD until a trivial **raw** feature has passed end-to-end through the framework.

## Next

1. Merge PR #4  
2. First `feature_type: raw` projection (e.g. adjusted close)  
3. Simple return / rolling features by family  
4. Label Generation ADR
