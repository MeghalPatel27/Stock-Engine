# ADR 05 — Feature Registry & Feature Store Design (Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [01-phase1.md](01-phase1.md), [04-phase3.md](04-phase3.md), [04-cleaning-review.md](04-cleaning-review.md)

**Hard rule:** No feature implementation (RSI, MACD, volatility, momentum, labels, etc.) until this ADR is **Finalized**.

---

## 1. Context

L1 published datasets are the only inputs for research/production features. Before computing any indicator, we need a registry and store design so features are named, versioned, point-in-time-safe, validated, and reusable — aligned with the signal contract and research/production split.

---

## 2. Decision summary (proposed)

| Topic | Proposal |
|---|---|
| What is a feature? | A named, versioned, typed column (or small column group) computed from L1 (or prior features) with declared lookback and PIT rules |
| Registry | YAML/JSON definitions under `docs/features/registry/` + loaded by code; single source of metadata |
| Store (V1) | Local Parquet under `data/features/` partitioned by `feature_set` / `as_of_date`; not a vendor feature platform |
| Naming | `{domain}__{name}__{window}` e.g. `mom__ret__5d`, `vol__realized__20d` |
| Versioning | `feature_version` per definition; bump on semantic change |
| PIT | Features for date T use only L1 rows with `session_date <= T` and lookbacks that do not peek |
| Nulls | Explicit policy per feature (propagate / skip / fail) |
| Lifecycle | `experimental` → `candidate` → `production` → `deprecated` |
| Consumers | Research may use experimental; production combiner/rank only `production` |
| Recompute | Same L1 + registry + config → identical feature Parquet (deterministic) |

---

## 3. What is a feature?

A **feature** is:

1. A deterministic function of one or more **published** datasets (normally L1) and/or other registered features  
2. Emitted as typed values keyed by `(isin, session_date)` unless cross-sectional-only  
3. Described by registry metadata (not tribal knowledge)  
4. Validated before publish  

A **feature set** is a versioned bundle of features computed together in one job (e.g. `alpha_v1`).

**Not features (yet):** model probabilities, ranks, labels — those are later phases that may *consume* features.

---

## 4. Feature naming conventions (proposed)

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

Examples:

- `mom__ret__1d`, `mom__ret__5d`  
- `vol__std__20d`  
- `liq__adv_inr__20d`  
- `cs__zscore__mom__ret__5d`  

Rules:

- lowercase, snake fragments, `__` separators  
- windows in trading days (`5d`) using canonical calendar  
- no ticker names inside feature names  

---

## 5. Feature metadata (registry schema)

Each feature YAML (proposed fields):

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Canonical name |
| `version` | yes | e.g. `v1` |
| `owner` | yes | person/role |
| `description` | yes | human meaning |
| `dtype` | yes | float / int / bool / category |
| `unit` | no | return, INR, dimensionless, … |
| `dependencies` | yes | list of datasets/features |
| `lookback_sessions` | yes | max trading days of history needed |
| `pit_rule` | yes | e.g. `asof_session_close` |
| `null_policy` | yes | `propagate` / `skip_row` / `fail_run` |
| `lifecycle` | yes | experimental/candidate/production/deprecated |
| `validation` | yes | min/max, finite, quantile caps, … |
| `recomputable` | yes | always `true` for V1 |

---

## 6. Dependencies & DAG

- Registry forms a DAG: features may depend on L1 datasets and upstream features.  
- Cycles forbidden.  
- Compute engine topologically sorts a feature set.  
- Missing dependency → fail closed for that feature set publish.  

---

## 7. Lookback windows & calendar

- All windows counted in **canonical trading_calendar** open sessions.  
- A feature with `lookback_sessions=20` on date T requires 20 prior open sessions of inputs (or applies null_policy).  
- No calendar-day shortcuts that ignore holidays.  

---

## 8. Point-in-time guarantees

1. Input only published L1 (and published upstream features) with `session_date <= T`.  
2. No use of `close_adj` from T+1 when computing T.  
3. Cross-sectional features use only the eligible universe **as-of T** (universe rules already Phase 1; wiring later).  
4. Feature publish stores `pit_as_of` / `as_of_date` + `config_hash` + registry hash.  

---

## 9. Feature versioning

| Change type | Action |
|---|---|
| Bugfix with same semantics | patch note; may keep `v1` if golden tests unchanged |
| Formula / window / null policy change | bump `version` → `v2`; do not overwrite `v1` outputs |
| Rename | new feature; deprecate old |

Storage path includes version:

```text
data/features/{feature_set}/{feature_version}/as_of_date=YYYY-MM-DD/*.parquet
```

---

## 10. Null handling (default policies)

| Policy | When |
|---|---|
| `propagate` | Insufficient lookback → NaN; downstream decides |
| `skip_row` | Drop ISIN-date from feature set output |
| `fail_run` | Structural expectation violated (e.g. missing L1) |

Default for rolling stats: **`propagate`**. Production feature sets may tighten.

---

## 11. Validation before publish

Per feature (fail closed for `production` lifecycle):

- dtype / finite checks  
- optional min/max  
- row-count vs L1 backbone  
- no future dates  
- registry hash recorded  

Experimental features may warn instead of fail (config flag).

---

## 12. Recomputability & goldens

- Same L1 snapshot + registry + config → byte-stable feature Parquet (aside from run_id/timestamps in lineage).  
- Golden feature fixtures required when first `production` feature set lands.  
- Lineage columns mirror cleaning: `run_id`, `config_hash`, `source dataset versions`.  

---

## 13. Storage layout (V1 local)

```text
data/
  features/
    {feature_set}/
      {feature_version}/
        as_of_date=YYYY-MM-DD/
          features.parquet
  metadata/
    features/
      manifests/
      published/
docs/
  features/
    registry/
      mom__ret__5d.yaml
      ...
```

No Feast/Tecton in V1 (budget + team size). Interface should allow a later backend swap.

---

## 14. Lifecycle

| State | Usable in research | Usable in production rank |
|---|---|---|
| experimental | yes | no |
| candidate | yes | no (paper only) |
| production | yes | yes |
| deprecated | read-only | no |

Promotion requires: registry complete, validation, golden or backtest note, owner ack (process light for 1–2 person team).

---

## 15. Relation to signal contract

Features are **inputs** to signals. A signal may wrap one or more features and must still emit:

`{value, direction, confidence, timestamp, version}`

The combiner never reads raw feature store internals — only signal contract (philosophy invariant).

---

## 16. Explicit non-goals for ADR-05 implementation phase

When implementing after approval, still **do not**:

- Train models  
- Generate labels / ranks  
- Build dashboard  

First implementation PR after ADR-05: registry loader + empty/feature-set scaffolding + 1–2 **example** production-candidate features only if sign-off says so; default recommendation: **registry + compute skeleton + one trivial smoke feature** (`mom__ret__1d`) gated experimental — confirm at sign-off.

---

## 17. Roadmap position

1. ✅ Charter … Phase 3 cleaning  
2. **→ ADR-05 Feature registry/store design (this doc)**  
3. Feature implementation (limited)  
4. Label generation  
5. Modeling → backtest → inference → serving  

---

## 18. Sign-off checklist

```text
§2 Decision summary table: APPROVE / CHANGE: ...
§3 Feature definition: APPROVE / CHANGE: ...
§4 Naming convention: APPROVE / CHANGE: ...
§5 Registry metadata fields: APPROVE / CHANGE: ...
§6 Dependencies DAG: APPROVE / CHANGE: ...
§7 Lookback via trading calendar: APPROVE / CHANGE: ...
§8 PIT rules: APPROVE / CHANGE: ...
§9 Versioning + path layout: APPROVE / CHANGE: ...
§10 Null policies: APPROVE / CHANGE: ...
§11 Validation fail-closed for production: APPROVE / CHANGE: ...
§12 Recomputability + goldens: APPROVE / CHANGE: ...
§13 Local Parquet store (no Feast V1): APPROVE / CHANGE: ...
§14 Lifecycle states: APPROVE / CHANGE: ...
§15 Signals wrap features (combiner sees signals only): APPROVE / CHANGE: ...
§16 First impl after approve: skeleton + experimental mom__ret__1d  OR  registry-only no compute: PICK A / B
Phase / ADR-05 overall: APPROVE / HOLD
```
