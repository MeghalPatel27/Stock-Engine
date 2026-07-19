# ADR 05 — Feature Registry & Feature Store

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [05-phase-feature-registry-proposal.md](05-phase-feature-registry-proposal.md)  
**Depends on:** [01-phase1.md](01-phase1.md), [04-phase3.md](04-phase3.md), [04-cleaning-review.md](04-cleaning-review.md)

## Sign-off amendments

1. Every feature declares **`feature_type`**: `raw` | `rolling` | `cross_sectional` | `derived` | `composite`.  
2. Optional metadata: **`computational_cost`** (`low` / `medium` / `high`), **`stability`** (`experimental` / `stable`).  
3. Organize features into **Feature Families** (momentum, trend, volatility, liquidity, …).  
4. First implementation = **PICK B — framework only** (no concrete feature compute such as `mom__ret__1d` until framework review).  

## Locked decisions

| Topic | Decision |
|---|---|
| What is a feature? | Named, versioned, typed value(s) from L1 / upstream features with lookback, PIT, and `feature_type` |
| Families | Features grouped under family ids (momentum, trend, volatility, liquidity, market_structure, cross_sectional, …) |
| Registry | YAML under `docs/features/registry/`; families in `docs/features/families.yaml` |
| Store V1 | Local Parquet under `data/features/` (no Feast/Tecton) |
| Naming | `{domain}__{metric}__{params}` |
| Versioning | Per-feature `version` (`v1`, `v2`, …); path includes version |
| PIT | Inputs with `session_date <= T` only; lookbacks use trading calendar |
| Nulls | Explicit `propagate` / `skip_row` / `fail_run` per feature |
| Lifecycle | `experimental` → `candidate` → `production` → `deprecated` |
| Validation | Fail-closed for `production` lifecycle |
| Recompute | Same L1 + registry + config → identical feature Parquet |
| Signals | Features feed signals; combiner sees **signals only** — never bypass |
| First code | Registry loader, metadata validation, DAG, storage interface, publisher + unit tests |

---

## 1. Context

L1 published datasets are the only inputs for research/production features. Before computing any indicator, we need a registry and store so features are named, versioned, point-in-time-safe, validated, and reusable — aligned with the signal contract and research/production split.

---

## 2. Decision summary

See locked table above. All §2–§15 proposals from the design review are **APPROVED**, with the sign-off amendments listed at the top.

---

## 3. What is a feature?

A **feature** is:

1. A deterministic function of one or more **published** datasets (normally L1) and/or other registered features  
2. Emitted as typed values keyed by `(isin, session_date)` unless cross-sectional-only  
3. Described by registry metadata (not tribal knowledge)  
4. Declared with an explicit **`feature_type`** for scheduling and dependency resolution  
5. Validated before publish  

A **feature set** is a versioned bundle of features computed together in one job (e.g. `alpha_v1`).

**Not features (yet):** model probabilities, ranks, labels — later phases that may *consume* features (via signals).

### Feature types

| `feature_type` | Meaning |
|---|---|
| `raw` | Thin projection / rename from a dataset |
| `rolling` | Windowed over trading sessions for one ISIN |
| `cross_sectional` | Uses the cross-section at session T |
| `derived` | Transform of one upstream feature |
| `composite` | Combines multiple upstream features |

---

## 4. Feature naming

```text
{domain}__{metric}__{params}
```

| Domain | Examples |
|---|---|
| `mom` | momentum / returns |
| `vol` | volatility |
| `liq` | liquidity |
| `trend` | MA / trend state |
| `cs` | cross-sectional rank/zscore of another feature |
| `reg` | regime inputs (later) |

Rules: lowercase; `__` separators; windows in trading days (`5d`); no ticker names inside feature names.

*(Concrete names such as `mom__ret__1d` are reserved for the Feature Implementation phase — not this framework PR.)*

---

## 5. Registry metadata

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Canonical name |
| `version` | yes | e.g. `v1` |
| `family` | yes | Family id from `families.yaml` |
| `feature_type` | yes | See §3 |
| `owner` | yes | person/role |
| `description` | yes | human meaning |
| `dtype` | yes | float / int / bool / category |
| `unit` | no | return, INR, dimensionless, … |
| `dependencies` | yes | `dataset:…` and/or `feature:…` refs |
| `lookback_sessions` | yes | max trading days of history needed |
| `pit_rule` | yes | V1: `asof_session_close` |
| `null_policy` | yes | `propagate` / `skip_row` / `fail_run` |
| `lifecycle` | yes | experimental / candidate / production / deprecated |
| `validation` | yes | finite, min/max, allow_null, … |
| `recomputable` | yes | always `true` for V1 |
| `computational_cost` | no | `low` / `medium` / `high` |
| `stability` | no | `experimental` / `stable` |

Identity: `feature_id = {name}@{version}`.

---

## 6. Feature families

Instead of a flat list, features belong to a family:

| Family id | Intent |
|---|---|
| `momentum` | Return / momentum style |
| `trend` | MA / trend state |
| `volatility` | Vol / range |
| `liquidity` | ADV / turnover / impact |
| `market_structure` | Structure inputs |
| `cross_sectional` | Ranks, z-scores, relative |
| `regime` | Regime (later) |
| `other` | Transitional |

Families live in `docs/features/families.yaml`. Unknown `family` → registry load fails. Families enable group enable/disable, importance analysis, and experiment comparison later.

---

## 7. Dependencies & DAG

- Registry forms a DAG: features may depend on L1 datasets and upstream features.  
- Cycles forbidden.  
- Compute order is a topological sort of the requested feature set.  
- Missing dependency → fail closed for that feature set publish.  

---

## 8. Lookback windows & calendar

- All windows counted in **canonical `trading_calendar`** open sessions.  
- A feature with `lookback_sessions=20` on date T requires 20 prior open sessions of inputs (or applies `null_policy`).  
- No calendar-day shortcuts that ignore holidays.  
- Framework helper: `stock_engine.features.calendar.sessions_on_or_before`.  

---

## 9. Point-in-time guarantees

1. Input only published L1 (and published upstream features) with `session_date <= T`.  
2. No use of `close_adj` from T+1 when computing T.  
3. Cross-sectional features use only the eligible universe **as-of T** (universe wiring later).  
4. Feature publish stores `as_of_date` + `config_hash` + `registry_hash`.  

---

## 10. Versioning & path layout

| Change type | Action |
|---|---|
| Bugfix with same semantics | patch note; may keep `v1` if goldens unchanged |
| Formula / window / null policy change | bump `version` → `v2`; do not overwrite `v1` outputs |
| Rename | new feature; deprecate old |

```text
data/features/{feature_set}/{feature_version}/as_of_date=YYYY-MM-DD/features.parquet
docs/features/registry/          # one YAML per feature (empty until Feature Implementation)
docs/features/families.yaml
```

---

## 11. Null handling

| Policy | When |
|---|---|
| `propagate` | Insufficient lookback → NaN; downstream decides |
| `skip_row` | Drop ISIN-date from feature set output |
| `fail_run` | Structural expectation violated (e.g. missing L1) |

Default for rolling stats: **`propagate`**. Production feature sets may tighten.

---

## 12. Validation before publish

Per feature (fail closed for `production` lifecycle):

- dtype / finite checks  
- optional min/max  
- no missing required columns  
- registry hash recorded  

Experimental features may skip value fail-closed checks (framework flag).

---

## 13. Recomputability & goldens

- Same L1 snapshot + registry + config → byte-stable feature Parquet (aside from run_id/timestamps in lineage).  
- Golden feature fixtures required when the first `production` feature set lands.  
- Lineage: `run_id`, `config_hash`, `registry_hash`, source dataset versions.  

---

## 14. Storage (V1 local Parquet)

No Feast/Tecton in V1. `FeatureStore` protocol allows a later backend swap. Publisher writes Parquet + optional metadata JSON under `data/metadata/features/published/`.

---

## 15. Lifecycle

| State | Research | Production rank |
|---|---|---|
| experimental | yes | no |
| candidate | yes | no (paper only) |
| production | yes | yes |
| deprecated | read-only | no |

---

## 16. Relation to signal contract

Features are **inputs** to signals. A signal may wrap one or more features and must still emit:

`{value, direction, confidence, timestamp, version}`

**The combiner never reads raw feature store internals — only the signal contract.** Do not bypass this abstraction.

---

## 17. First implementation (PICK B)

Implement and review **framework only**:

- Registry loader + metadata validation (`feature_type`, families, optional cost/stability)  
- Dependency DAG validation  
- Feature storage interfaces (`LocalParquetFeatureStore`)  
- Feature publishing framework (validate + write + manifest)  
- Trading-calendar lookback helper  
- Unit tests + fixture YAML under `tests/fixtures/features/`  

**Do not** implement concrete feature formulas (including `mom__ret__1d`) until the framework is reviewed.

---

## 18. Refined roadmap

1. ✅ Project Charter  
2. ✅ Phase 1 — Problem Formulation  
3. ✅ Phase 0 — Foundations  
4. ✅ Phase 2 — Data Acquisition  
5. ✅ Phase 3 — Cleaning & Normalization  
6. ✅ ADR-05 — Feature Registry & Store Design  
7. ✅ Feature Framework Implementation (registry, DAG, publishing, validation, storage)  
8. **→ Feature Implementation** — start with `raw__close_adj__l1`, then Momentum / Trend / Vol / Liq  

9. Label Generation ADR  
10. Label implementation  
11. Modeling ADR  
12. Model implementation  
13. Backtesting  
14. Inference  
15. Serving  

---

## Explicit non-goals (framework phase)

No RSI/MACD/momentum/volatility/liquidity compute. No labels. No models. No ranking. No backtests. No NSE downloaders in `src/`.

---

## Framework review follow-ups (post sign-off)

Architecture review **APPROVED** the framework with five required improvements before Feature Phase:

| # | Item | Status |
|---|---|---|
| 1 | Duplicate `(isin, session_date)` fail-closed in publish | **Done** — `validate_publish_frame` |
| 2 | Dataset registry + existence validation for `dataset:` deps | **Done** — `docs/features/datasets.yaml` + loader checks |
| 3 | Feature content hashing on published manifests | **Done** — `feature_content_hash` |
| 4 | Incremental recomputation (new dates / affected ISINs) | **Deferred** — see below |
| 5 | Registry lint command for CI | **Done** — `stock-engine-lint-features` |

### Deferred: incremental recomputation

V1 publish writes a full feature-set frame for an `as_of_date`. Incremental recompute (only new sessions or affected ISINs) is explicitly **out of scope** for the first feature wave. Track as a future enhancement / mini-ADR after several production features exist and rebuild cost matters.

Schema compatibility matrices (feature ↔ dataset `schema_version`) are also deferred until multiple dataset schema versions coexist.

### First feature after merge

Start with a **raw projection** feature (e.g. expose `close_adj` via `feature_type: raw`) to validate registry → compute → publish → manifest → store end-to-end. Then simple return/rolling features. RSI/MACD only later.
