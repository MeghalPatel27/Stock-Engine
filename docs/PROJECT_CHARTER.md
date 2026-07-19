# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** ADR-08 Backtesting **Finalized**. Harness runs on published real pilot data.

## Progress

| Step | Status |
|---|---|
| Charter / Philosophy | ✅ |
| Phase 1 Problem formulation | ✅ |
| Phase 0 Foundations | ✅ |
| Phase 2 Data acquisition | ✅ |
| Phase 3 Cleaning & normalization | ✅ |
| ADR-05 Feature registry & store | ✅ |
| Feature backlog (25) | ✅ |
| ADR-06 Label generation | ✅ E2E APPROVED |
| ADR-07 Modeling | ✅ Finalized + PICK A |
| ADR-08 Backtesting | ✅ Finalized + harness |
| Inference / Serving ADR | ⏭️ next |

## Hard stop

Do not begin live serving until Inference/Serving ADR is signed off.  
Pilot backtest metrics are **not** production benchmarks (5-name universe).

## Next

1. Review backtest harness + pilot metrics  
2. Inference / Serving ADR  
3. Production universe (`phase1_filters`) when membership tables land
