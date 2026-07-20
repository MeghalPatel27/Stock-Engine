# ADR 09 — Inference & Serving

**Status:** Finalized  
**Date locked:** 2026-07-20  
**Depends on:** [00-philosophy.md](00-philosophy.md), [01-phase1.md](01-phase1.md), [07-modeling.md](07-modeling.md), [08-backtesting.md](08-backtesting.md)

## Locked decisions

| Topic | Decision |
|---|---|
| Daily path | Published features + frozen model → `RankRow` publish (**never labels**) |
| Decision session | Default `session_date = as_of_date` (post-close) |
| Inputs | `data/features/{set}/{ver}/…` + `data/models/{name}/{ver}/` + L1 symbol map |
| Outputs | `data/ranks/{rank_set}/{rank_version}/horizon=H/as_of_date=…/ranks.parquet` |
| Metadata | `data/metadata/ranks/published/{as_of}/…` + run metadata |
| Top-N | Emit full ranks; paper lists use `output.top_n_longs` / `top_n_shorts` |
| Signals | Wrap directional heads as `Signal` rows alongside ranks (V1 combiner = identity) |
| Overwrite | Refuse unless `--overwrite` or version bump |
| Live brokers | **Out of scope** — local publish only |
| Fail-closed | Missing features/model/allow-list, empty panel, duplicate keys, label columns present |

## Pipeline

```text
as_of close
  → load published features (session ≤ as_of)
  → load frozen model_version + feature allow-list
  → score → RankRows (+ Signals)
  → validate → publish Parquet + manifest
```

Labels remain train/eval only. Production code never imports `research/`.

## First implementation

`stock-engine-infer` CLI + store + tests on published pilot artifacts (`as_of=2026-07-17`).

## Explicit non-goals

No broker/API orders. No scheduling daemon. No multi-horizon blend. No online retraining.
