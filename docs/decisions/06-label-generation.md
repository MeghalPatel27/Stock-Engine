# ADR 06 — Label Generation

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [06-phase-label-generation-proposal.md](06-phase-label-generation-proposal.md)  
**Depends on:** [01-phase1.md](01-phase1.md), [04-phase3.md](04-phase3.md), [05-feature-registry.md](05-feature-registry.md)

## Sign-off amendments

1. Quantile cut size uses configurable **`selection_policy`**: `floor` | `ceil` | `nearest` (default **`floor`**).  
2. Universe modes: **`pilot`** | **`l1_intersection`** | **`phase1_filters`**.  
   - `pilot` is **not suitable for production benchmarking**.  
3. Every published label row stores **`top_quantile`** and **`bottom_quantile`**.  
4. Publish **fails closed** on duplicate `(isin, session_date, horizon, label_version)`.  
5. First implementation = **PICK A** — horizon **H=5** only.  

Also locked from review recommendations: `sample_weight` (default 1.0), `label_source` (default `price_return_v1`), never silently rewrite prior versions (refuse overwrite unless explicit rebuild / version bump).

## Locked decisions

| Topic | Decision |
|---|---|
| Label | Ternary `bullish` / `bearish` / `neutral` |
| Forward return | `CloseAdj(T+H)/CloseAdj(T)-1` on trading calendar |
| Primary horizon | H=5 |
| Selection policy | Configurable; default `floor` |
| Tie-break | Bullish: `(R desc, isin asc)`; bearish: `(R asc, isin asc)` |
| Universe modes | `pilot` / `l1_intersection` / `phase1_filters` |
| Store | `data/labels/{label_set}/{label_version}/horizon=H/as_of_date=...` |
| Inference | Labels **never** on live path |
| First code | H=5 compute → validate → Parquet → manifest + tests |

## Pipeline

```text
L1 close_adj + trading_calendar
  → forward returns R(T,5)
  → CS quantile classes (deterministic ISIN ties)
  → validate (incl. duplicate keys)
  → publish Parquet + manifest
```

Training join later: `features(T) ⋈ labels(T, H=5)` only when `T+5` is known.

## Explicit non-goals

No 1d/20d labels yet. No models. No ranking. No purged CV. No RSI/MACD.
