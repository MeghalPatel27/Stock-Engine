# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-20  
**Status:** ADR-09 Inference & Serving **Finalized**. Daily rank publish implemented (local; no brokers).

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
| ADR-09 Inference & Serving | ✅ Finalized + local publish |
| Per-stock models (pilot) | ✅ Tuned one model per ISIN |
| Production universe / live brokers | ⏭️ later |

## Hard stop

No live broker orders until a future Live-Trading ADR.  
Pilot metrics remain **not** production benchmarks.

## Next

1. Review daily `stock-engine-infer` on pilot  
2. Promote features + expand universe (`phase1_filters`)  
3. Model quality iteration (still research/)
