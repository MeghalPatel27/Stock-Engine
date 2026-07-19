# Cleaning Implementation Review — Record

**Status:** Approved  
**Date:** 2026-07-19  
**Applies to:** [04-phase3.md](04-phase3.md) implementation on `main`

## Verdict

**APPROVE** cleaning implementation and architecture. Follows ADR-04 and prior invariants.

## Non-blocking / deferred

| Item | Disposition |
|---|---|
| Decimal (or equivalent) for cumulative CA factors | Deferred post-V1; float OK for V1 with golden-dataset guards |

## Required before feature engineering (this commit)

1. Explicit CA regression fixture tests (split/bonus/sequential/symbol/merger/missing factor)  
2. Persist `cumulative_adjustment_factor` + `adjustment_method` on L1 rows  
3. Version adjustment methodology: `backward_price_return_v1`  
4. Golden benchmark datasets under `tests/golden/`  
5. Published-dataset metadata sidecar (schema/dataset/adjustment/config/run)  

## Next

**ADR-05 — Feature Registry & Feature Store Design** — design only; no feature implementation until finalized.
