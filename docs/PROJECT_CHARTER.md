# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** V1 planned feature backlog implemented (25 features). Next: labels ADR.

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
| Feature backlog (raw/mom/trend/vol/liq/cs) | ✅ 25 features |
| Label Generation ADR | ⏭️ next |
| Labels → models → backtest → serve | ⛔ blocked |

## Hard stop

Do not implement RSI/MACD yet. Next architecture gate is **Label Generation ADR**.

## Next

1. Review / promote features (experimental → candidate → production)  
2. Label Generation ADR  
3. Labels → modeling ADR
