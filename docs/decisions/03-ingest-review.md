# Ingest Architecture Review — Record

**Status:** Approved  
**Date:** 2026-07-19  
**Applies to:** [03-phase2.md](03-phase2.md) implementation on `main`

## Verdict

**APPROVE** ingest architecture:

1. Provider abstraction (`DataSource` + `LocalIncomingCsvSource`)  
2. `incoming → raw → validation → clean`  
3. Raw immutability + SHA-256  
4. Metadata (runs, manifests, dataset versions)  
5. Clean Parquet only (CSV only as incoming staging / test fixtures)  

## Explicit non-goals (reconfirmed)

Do **not** start: feature engineering, signals, labels, probabilities, model training, ranking, backtesting.

## Requirements to address in Phase 3 (not blockers for current ingest)

| ID | Requirement |
|---|---|
| R1 | Dataset **schema versioning** (e.g. `equity_eod_schema=v1`) |
| R2 | Explicit **duplicate keys** per dataset (fail closed) |
| R3 | **Lineage** on every clean dataset: source file, raw checksum, ingestion timestamp |
| R4 | Explicit detection of **missing trading sessions** |
| R5 | Single **canonical trading calendar** as source of truth |

These are designed in [04-phase3-proposal.md](04-phase3-proposal.md) and implemented only after that ADR is finalized.
