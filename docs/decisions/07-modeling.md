# ADR 07 — Modeling

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [07-phase-modeling-proposal.md](07-phase-modeling-proposal.md)  
**Depends on:** [00-philosophy.md](00-philosophy.md), [01-phase1.md](01-phase1.md), [02-phase0.md](02-phase0.md), [05-feature-registry.md](05-feature-registry.md), [06-label-generation.md](06-label-generation.md)

## Sign-off amendments

1. Ranking scores use configurable **`risk_weight`**:  
   `score = p × confidence × (1 - risk_weight × risk)` (long/short with `p_bullish` / `p_bearish`).  
2. Evaluation metrics include **Precision@20** alongside Top-K hit-rate / rank IC.  
3. First implementation = **PICK A**.  
4. Heads = **independent binary**; calibration **deferred**; train window = **expanding**.

## Locked decisions

| Topic | Decision |
|---|---|
| Objective | CS probability of top/bottom quantile (ADR-01) |
| Horizon | H=5 only (V1) |
| Train join | `features(T) ⋈ labels(T, H=5)` when label known |
| Inference | Features (→ signals) only — **never labels** |
| Model family | Gradient-boosted trees (sklearn HGB / LightGBM-class); two binary heads |
| Simplex | Not required |
| CV | Expanding walk-forward + purge + embargo `E=H=5` |
| Metrics | Rank IC, Top-K hit-rate, **Precision@20**, fold stability; calibration secondary |
| Calibration | Deferred (raw scores) |
| Ranking | `p * confidence * (1 - risk_weight * risk)`; `risk_weight` config |
| Artifacts | Versioned under `data/models/`; never silent overwrite |
| Research vs prod | Train in `research/`; prod loads freeze only |
| First code | PICK A — join, purged WF, freeze, thin RankRow scorer |

## Pipeline

```text
features(T) ⋈ labels(T, H=5)
  → purged expanding walk-forward
  → two-head GBT (p_bullish, p_bearish)
  → freeze model_version + allow-list
  → score → Signals → Combiner → RankRow
```

## Explicit non-goals

No live serving. No H=1/20. No portfolio backtest (Backtesting ADR). No learned combiner. No forced calibration.
