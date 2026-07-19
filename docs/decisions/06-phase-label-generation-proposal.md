# ADR 06 — Label Generation Design (Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [01-phase1.md](01-phase1.md), [04-phase3.md](04-phase3.md), [05-feature-registry.md](05-feature-registry.md)

**Hard rule:** No label implementation, model training, or ranking code until this ADR is **Finalized**.

---

## 1. Context

Features are published. Training and evaluation need **labels**: the supervised targets that match Phase 1’s objective — cross-sectional probability of landing in the top/bottom forward-return quantiles of the tradable universe.

Labels are **not features** and **not signals**. Models consume features (via signals later); labels exist only for research/training/evaluation and are never an inference-time input.

---

## 2. Decision summary (proposed)

| Topic | Proposal |
|---|---|
| What is a label? | Ternary class for name `i` as-of session `T` and horizon `H`: `bullish` / `bearish` / `neutral` |
| Target quantity | Forward close-to-close return on **L1 adjusted close** over `H` trading sessions |
| Assignment | Cross-sectional quantiles within the **eligible label universe** on day `T` |
| Primary horizon | **H = 5** first (`labels.horizon_primary`) |
| Other horizons | 1d / 20d later as separate label sets (no blend) |
| Quantiles | Top `label_top_quantile` (default 0.20) / bottom `label_bottom_quantile` (default 0.20) / middle neutral |
| Missing forward close | **Exclude** row from that day’s label set (no imputation) |
| Store V1 | Local Parquet under `data/labels/` (same spirit as feature store; no Feast) |
| PIT / leakage | Labels for `T` require `Close(T+H)`; training joins features@`T` with labels@`T` only when `T+H` is known |
| Consumers | Research / training / evaluation only — combiner and live inference **never** read labels |
| First code after approve | Label computer + store + publish + unit tests for H=5 only |

---

## 3. Formal definitions

### 3.1 Forward return

```text
R_i(T, H) = CloseAdj_i(T+H) / CloseAdj_i(T) - 1
```

- `CloseAdj` = L1 `close_adj`  
- `T+H` = H **open** sessions after `T` on the canonical `trading_calendar`  
- If `CloseAdj_i(T)` or `CloseAdj_i(T+H)` is missing → no label for `(i, T, H)`

### 3.2 Label class

Within the eligible set `U(T, H)` = names that (a) pass the label-universe filter for `T` and (b) have valid `R_i(T, H)`:

| Class | Rule (defaults) |
|---|---|
| `bullish` | `R` in top `label_top_quantile` of `U(T, H)` |
| `bearish` | `R` in bottom `label_bottom_quantile` of `U(T, H)` |
| `neutral` | remainder |

Config keys (already in `config/default.yaml`):

- `labels.top_quantile` (default 0.20)  
- `labels.bottom_quantile` (default 0.20)  
- `labels.horizon_primary` (default 5)

### 3.3 Deterministic tie-break

When returns tie at a quantile boundary, break ties by ascending `isin` so labels are reproducible.

Quantile method proposal: use rank-based cutoffs — sort by `(R desc, isin asc)` for bullish top-k and `(R asc, isin asc)` for bearish bottom-k, with  
`k_top = max(1, floor(n * top_quantile))` when `n >= 1`, else empty day.  
(Exact `floor` vs `round` — confirm at sign-off; recommendation: **floor** with `max(1, …)` only when `n * q >= 1`, else 0.)

**Recommended V1 rule:**

```text
n = |U(T, H)|
k_top = floor(n * top_quantile)
k_bot = floor(n * bottom_quantile)
```

If `k_top + k_bot > n`, shrink `k_bot` so `k_top + k_bot <= n`.  
If `k_top == 0` or `k_bot == 0` for small `n`, that class is empty for the day (acceptable for tiny universes / pilots).

---

## 4. Label universe vs trading universe

| Concern | Proposal |
|---|---|
| Label universe `U(T, H)` | Same eligibility intent as Phase 1 trading universe **as-of T** (F&O ∩ liquidity/price ∩ not excluded) |
| V1 practicality | Until full universe membership tables are wired, use **all ISINs present in L1 equity on T with valid forward return** as a transitional label universe, versioned as `universe_mode: l1_intersection` |
| Production mode | `universe_mode: phase1_filters` once weekly F&O membership + ADV/price filters are implemented |

Both modes must be recorded on the label manifest.

---

## 5. Point-in-time & leakage

1. Features for session `T` use only data with `session_date <= T`.  
2. Labels for session `T` use `Close(T+H)` — available only after session `T+H` closes.  
3. Training row for date `T` is valid only when the as-of publish date `D >= T+H` (label known).  
4. Live inference on date `D` predicts ranks for `D` **without** labels.  
5. Do not attach `R_i(T, H)` or future closes into feature frames.

### Overlapping samples

Forward returns for consecutive `T` overlap in calendar span. V1 proposal:

- **Allow overlapping training rows** (simple).  
- Document that purged CV / embargo is a **later** modeling concern (Modeling ADR), not a label-store requirement.

---

## 6. Label schema (row contract)

Each published label row:

| Column | Type | Meaning |
|---|---|---|
| `isin` | string | Canonical id |
| `session_date` | date | As-of session `T` |
| `horizon` | int | `H` in trading sessions |
| `forward_return` | float | `R_i(T, H)` |
| `label` | category | `bullish` / `bearish` / `neutral` |
| `universe_size` | int | `n = \|U(T, H)\|` |
| `label_version` | string | e.g. `v1` |
| `universe_mode` | string | `l1_intersection` or `phase1_filters` |

Unique key: `(isin, session_date, horizon, label_version)`.

---

## 7. Storage layout (V1 local Parquet)

```text
data/labels/
  {label_set}/
    {label_version}/
      horizon={H}/
        as_of_date=YYYY-MM-DD/
          labels.parquet
data/metadata/labels/published/
  {as_of_date}/
    {label_set}__{label_version}__h{H}.json
```

Proposed defaults: `label_set=core`, `label_version=v1`, primary `horizon=5`.

Manifest fields (mirror features): `run_id`, `config_hash`, `config_version`, `label_content_hash`, `registry` N/A, `row_count`, quantile settings, `universe_mode`.

---

## 8. Validation (fail-closed)

Before publish:

- Required columns present  
- No duplicate `(isin, session_date)` within a horizon file  
- `label ∈ {bullish, bearish, neutral}`  
- `forward_return` finite when row present  
- Class counts consistent with `k_top` / `k_bot` / remainder for each `session_date`  
- No `session_date` with `max(session_date)+H` beyond available calendar/L1 when building through as-of `D` — only emit labels for `T` where `T+H <= last_available_session`

---

## 9. Recomputability

Same L1 + calendar + config quantiles + `universe_mode` + `label_version` → identical label Parquet (aside from run_id timestamps in metadata). Content hash on sorted frame (same approach as features).

---

## 10. Relation to features & signals

```text
L1 → Features → (later) Signals → Combiner / Model → Ranks
                ↘ Labels (training only)
```

- Training join: `features(session_date=T)` ⋈ `labels(session_date=T, horizon=H)`  
- Combiner / live path: **signals only** (philosophy invariant) — labels never injected

---

## 11. Versioning

| Change | Action |
|---|---|
| Quantile defaults / tie-break / universe_mode semantics | bump `label_version` |
| Bug fix with identical semantics + goldens | may keep `v1` |
| New horizon | same version OK; separate `horizon=` partition |

---

## 12. First implementation after approval (proposed)

**PICK A (recommended):** Label pipeline for **H=5 only**

- Load L1 + calendar  
- Compute `R_i(T, 5)`  
- Assign classes with deterministic ties  
- Validate + write Parquet + manifest  
- Unit tests + pilot smoke  

**PICK B:** Design-only docs (no code) until a second review  

**Not in first label PR:** model training, ranking, 1d/20d labels, purged CV, production universe filters beyond `l1_intersection`.

---

## 13. Explicit non-goals

- No RSI/MACD or new features in this phase  
- No model training / RankRow emission  
- No backtest portfolio construction  
- No live serving of labels  

---

## 14. Roadmap position

1. ✅ … Feature backlog (25)  
2. **→ ADR-06 Label Generation (this doc)**  
3. Label implementation (H=5)  
4. Modeling ADR  
5. Model implementation  
6. Backtesting → Inference → Serving  

---

## 15. Sign-off checklist

```text
§2 Decision summary table: APPROVE / CHANGE: ...
§3 Formal definitions (return + classes + tie-break): APPROVE / CHANGE: ...
§4 Label universe modes: APPROVE / CHANGE: ...
§5 PIT / leakage / overlapping samples: APPROVE / CHANGE: ...
§6 Row schema: APPROVE / CHANGE: ...
§7 Storage layout: APPROVE / CHANGE: ...
§8 Validation fail-closed: APPROVE / CHANGE: ...
§9 Recomputability + content hash: APPROVE / CHANGE: ...
§10 Features/signals boundary (labels training-only): APPROVE / CHANGE: ...
§11 Versioning: APPROVE / CHANGE: ...
§12 First impl after approve: PICK A (H=5 code) / PICK B (docs only)
Phase / ADR-06 overall: APPROVE / HOLD
```
