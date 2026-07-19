# ADR-06 Label Pipeline — Review Packet

**Repo:** MeghalPatel27/Stock-Engine  
**Status:** **APPROVE** (E2E review 2026-07-19). Modeling ADR unblocked (docs only).  
**Hard rule:** Do not begin model implementation until the Modeling ADR is reviewed and approved.

## Ask of reviewer

1. Label semantics — Approve / Change  
   (forward return, quantile cuts, `selection_policy`, tie-break, universe modes)
2. Leakage / PIT — Approve / Change  
   (features at T, labels at T+H, training join)
3. Storage / versioning / fail-closed validation — Approve / Change  
   (Parquet layout, embedded quantiles, duplicate-key fail, no silent overwrite)
4. Is H=5 PICK A complete enough to unblock the **Modeling ADR proposal** (docs only)?

## Sign-off result

| Section | Verdict |
|---|---|
| Label semantics | APPROVE |
| PIT / leakage | APPROVE |
| Storage / versioning / validation | APPROVE |
| H=5 completeness | APPROVE |
| **Overall** | **APPROVE** |
| Unblock Modeling ADR (docs)? | **YES** |

## Sign-off amendments already locked

1. Configurable `selection_policy`: `floor` | `ceil` | `nearest` (default `floor`)
2. Universe modes: `pilot` | `l1_intersection` | `phase1_filters`  
   — `pilot` is **not suitable for production benchmarking**
3. Every published row stores `top_quantile` and `bottom_quantile`
4. Publish fails on duplicate `(isin, session_date, horizon, label_version)`

Also present: `sample_weight` (default 1.0), `label_source` (`price_return_v1`), refuse overwrite unless `--overwrite` / version bump.

## Tie-break (locked)

- Bullish top-k: sort `(forward_return desc, isin asc)`, take first `k_top`
- Bearish bottom-k: sort `(forward_return asc, isin asc)`, take first `k_bot`
- On rare overlap after size shrink, bullish wins

## What shipped

| Piece | Path |
|---|---|
| ADR final | `docs/decisions/06-label-generation.md` |
| Compute / validate | `src/stock_engine/labels/compute.py` |
| Quantile policy | `src/stock_engine/labels/quantiles.py` |
| Pipeline + CLI | `src/stock_engine/labels/pipeline.py`, `cli.py` |
| Store | `src/stock_engine/labels/store.py` |
| Config | `config/default.yaml` → `labels.*` |
| Docs | `docs/labels/README.md` |
| Unit + E2E | `tests/unit/labels/` + `tests/fixtures/labels/incoming/` |

## Next

See [07-phase-modeling-proposal.md](../decisions/07-phase-modeling-proposal.md).
