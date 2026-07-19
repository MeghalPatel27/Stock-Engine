# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** Phase 3 cleaning implemented (L0/L1). Awaiting cleaning review. **Next design phase: Feature Registry & Feature Store — before any feature/label code.**

## Finalized ADRs

| ADR | Doc |
|---|---|
| 00 Philosophy | [decisions/00-philosophy.md](decisions/00-philosophy.md) |
| 01 Problem formulation | [decisions/01-phase1.md](decisions/01-phase1.md) |
| 02 Foundations | [decisions/02-phase0.md](decisions/02-phase0.md) |
| 03 Data acquisition | [decisions/03-phase2.md](decisions/03-phase2.md) |
| 04 Cleaning & CA methodology | [decisions/04-phase3.md](decisions/04-phase3.md) |

## Implemented

- Local CSV ingest → immutable raw + SHA-256  
- L0 normalized Parquet + lineage + schema versions  
- Canonical `trading_calendar` + missing-session detection (N configurable, default 5)  
- L1 backward **price-return** adjustment (raw + adj); ordinary dividends not applied to price-return  
- Data dictionaries under `docs/data/dictionary/`  

## Hard stop

Do **not** start technical indicators, ML features, labels, probabilities, models, ranking, or backtesting until:

1. This cleaning layer is reviewed/approved, and  
2. A **Feature Registry & Feature Store** design ADR is written and signed off.

## What's needed from you

Architecture review of the Phase 3 cleaning implementation (L0/L1 outputs + CA policy).
