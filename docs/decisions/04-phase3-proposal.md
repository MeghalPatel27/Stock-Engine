# ADR 04 — Phase 3: Data Cleaning, Normalization & Corporate Action Methodology (Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [01-phase1.md](01-phase1.md), [02-phase0.md](02-phase0.md), [03-phase2.md](03-phase2.md), [03-ingest-review.md](03-ingest-review.md)

**Hard rule:** No feature engineering, labels, models, ranking, or backtesting until this ADR is finalized **and** the cleaning pipeline implementing it is reviewed.

This document defines how ingested raw CSVs become **canonical, point-in-time-safe clean datasets**, including corporate-action adjustment, missing-data policy, outliers, identity lifecycle, calendar ownership, schema versioning, duplicate keys, and lineage.

---

## 1. Context

Phase 2 delivers: local CSV → immutable raw → DQ → staged clean Parquet.  
Phase 3 must make that clean layer **research-correct**: adjusted prices, complete sessions, traceable lineage, and reconstructible history — without yet computing features or labels.

---

## 2. Decision summary (proposed)

| Topic | Proposal |
|---|---|
| Pipeline stages | `raw` → **normalize/validate** → **adjust (CA)** → **canonical clean** (versioned) |
| Price adjustment | **Backward-adjusted** OHLC for return research (see §5) |
| Dividends | Track in CA table; **do not** adjust prices for ordinary cash dividends in V1 returns (split/bonus/demerger factors only) — confirm at sign-off |
| Canonical id | **ISIN** (+ map history for symbol changes) |
| Calendar | Single canonical **NSE equity session calendar** dataset |
| Missing sessions | Detect vs calendar; **fail closed** for publish if gap in required window (configurable) |
| Schema version | Every dataset carries `schema_version` |
| Duplicate keys | Explicit unique keys per dataset; duplicates fail |
| Lineage | Clean tables + manifests store source file, raw SHA-256, ingestion timestamp |
| Outliers | Soft-flag extreme moves; hard-fail only on structural impossibilities in V1 |
| Output | Parquet only under `data/clean/`; no production CSV |

---

## 3. Layered clean model

Clarify two publish tiers (names proposed):

| Tier | Path (proposed) | Contents |
|---|---|---|
| **L0 — Normalized** | `clean/l0/<dataset>/` | Typed, column-normalized, DQ-passed, **unadjusted** prices; lineage columns |
| **L1 — Canonical research** | `clean/l1/<dataset>/` | CA-adjusted series + calendar-aligned panels; used by all later phases |

V1 Phase 2 today roughly equals a first cut of L0. Phase 3 introduces explicit L0/L1 and upgrades lineage/schema/calendar.

**Rule:** Features/labels (later) read **L1 only**, never raw or incoming.

---

## 4. Schema versioning (Gap R1)

Every dataset declares a schema id + version in config and in Parquet metadata / manifest:

| Dataset | Initial schema |
|---|---|
| `equity_eod` | `equity_eod_schema` = `v1` |
| `corporate_actions` | `corporate_actions_schema` = `v1` |
| `symbol_isin_map` | `symbol_isin_map_schema` = `v1` |
| `trading_calendar` | `trading_calendar_schema` = `v1` |
| `security_master` | `security_master_schema` = `v1` (listing dates, status) |

**Rules:**

1. Ingest rejects files that cannot be mapped to a known schema version.  
2. Breaking column/semantics changes bump schema version; migration note required in ADR or `docs/data/migrations/`.  
3. `dataset_version` (content/build) ≠ `schema_version` (shape/semantics). Both persisted.

---

## 5. Corporate-action adjustment methodology (core)

### 5.1 Actions in scope for V1 price adjustment

| Action type | Adjust prices? | Notes |
|---|---|---|
| Split / subdivision / consolidation | **Yes** | Factor from ratio |
| Bonus / stock dividend | **Yes** | Factor from ratio |
| Rights (if factor supplied) | **Yes** if factor present; else flag & exclude window |
| Demerger / spin-off | **Yes** if factor present; else **exclude** ISIN from returns until resolved |
| Merger / amalgamation | **Identity event** — map old→new ISIN; exclude event window from labels |
| Ordinary cash dividend | **No price adjust in V1** | Store in CA table for later total-return research |
| Symbol change only | No price adjust | Update `symbol_isin_map` / security master |

### 5.2 Adjustment direction — **propose backward-adjusted**

**Backward-adjusted:** latest price matches recent market quotes; history is scaled so that **close-to-close returns** are continuous across splits/bonuses.

| Approach | Pros | Cons |
|---|---|---|
| **Backward (proposed)** | Matches common vendor “adj close”; easy eyeball vs live quotes | Historical levels change when new CA arrives (must rebuild L1) |
| Forward-adjusted | Historical levels stable once written | Latest price ≠ exchange print; confusing for ops |

**V1 choice (proposed):** Backward-adjust OHLC (and volume inversely when split/bonus factor applies). Persist both:

- `close_raw` (unadjusted)  
- `close_adj` (backward-adjusted)  
- same for open/high/low when present  

Phase 1 labels use **`close_adj(T+H)/close_adj(T) - 1`**.

**Rebuild rule:** Any new/changed CA for an ISIN triggers **L1 rebuild** for that ISIN (and full panel rebuild acceptable in V1 given local scale).

### 5.3 Factor application

For event on `ex_date` with price factor `f` (new shares / old shares style normalized so post-split price ≈ pre/f):

- All **raw** sessions with `session_date < ex_date` get prices multiplied by the cumulative product of subsequent factors (standard backward adj).  
- Exact factor algebra documented in implementation notes; must be unit-tested on fixtures (2:1 split, 1:2 bonus, etc.).

If `ratio_num`/`ratio_den`/`factor` missing for an adjusting action type → **DQ fail** for that CA row (fail closed for L1 publish of that ISIN until fixed).

---

## 6. Duplicate keys (Gap R2) — proposed unique keys

| Dataset | Unique key (fail if duplicate) |
|---|---|
| `equity_eod` | `(isin, session_date)` |
| `corporate_actions` | `(isin, ex_date, action_type)` — extend with `factor`/`notes` hash only if real collisions require it later |
| `symbol_isin_map` | `(isin, symbol, valid_from)` with null `valid_from` treated as `0001-01-01` |
| `trading_calendar` | `(session_date)` |
| `security_master` | `(isin)` as-of versioned SCD2 optional later; V1 unique `(isin)` current row |

Also reject duplicate `(symbol, session_date)` in equity_eod when symbol present (identity smell), even if ISINs differ — surface as DQ error for human fix.

---

## 7. Lineage (Gap R3)

Every L0/L1 Parquet publish must include (table columns and/or sidecar manifest — **propose both**):

| Field | Meaning |
|---|---|
| `source_file` | Original incoming filename |
| `raw_sha256` | Checksum of immutable raw bytes |
| `ingested_at` | Ingestion timestamp (UTC) |
| `provider` | e.g. `local_csv` |
| `schema_version` | e.g. `v1` |
| `dataset_version` | Build/content version |
| `run_id` | Ingest/clean run id |

Row-level: broadcast lineage columns onto each row (simple V1) **or** join via `run_id` + dataset manifest. **Propose row-level broadcast** for debuggability at small scale.

---

## 8. Canonical trading calendar (Gap R5)

### 8.1 Ownership

Introduce dataset **`trading_calendar`** as the **single source of truth** for NSE equity sessions.

| Column | Notes |
|---|---|
| `session_date` | Trading day |
| `is_open` | true for sessions |
| `source` | e.g. `user_csv` / `derived` |
| `schema_version` | |

### 8.2 V1 supply path

Same as other data: user drops `trading_calendar.csv` into `data/incoming/` (or dated form).  
Optional helper (later): derive candidate sessions from distinct `equity_eod.session_date` — **but derived calendar cannot silently override** an explicit calendar file when present.

### 8.3 Consumers

- Missing-session detection  
- Horizon T+N trading-day arithmetic (Phase 1)  
- Universe/as-of alignment  

**Proposal:** Calendar becomes a **required** dataset for L1 publish (alongside equity_eod + corporate_actions).

---

## 9. Missing session policy (Gap R4)

For each ISIN in the active universe / present in equity_eod:

1. Expected sessions = calendar open dates in `[min_date, as_of_date]` (or configured lookback).  
2. Observed = distinct `session_date` for that ISIN.  
3. `missing = expected - observed` (excluding known listing date / delist windows from security master when available).

**V1 policy (proposed):**

| Severity | Rule |
|---|---|
| Hard fail L1 panel publish | Any missing session in the **last N calendar trading days** for an ISIN that traded before the gap (default **N=5**, configurable) |
| Warn + manifest list | Gaps older than N days |
| Exclude ISIN from L1 panel | If listing date unknown and history too sparse (configurable min sessions) |

Never silently fill missing OHLC with forward-fill for **return labels**. Optional research ffill is out of scope until later and must be flagged if ever added.

---

## 10. Missing data & halt handling (prices)

| Case | Policy |
|---|---|
| Missing `close` | Already hard-fail at ingest DQ |
| Missing OHLC but close present | Allowed; adj applies to available fields |
| Zero / negative prices | Hard-fail row |
| Halt day present with OHLC | Keep row; later exclusion lists may drop from ranking (Phase 1 exclusions) |
| ISIN appears after listing date with gap | Missing-session rules apply |

---

## 11. Outlier detection (V1 lean)

| Check | Action |
|---|---|
| Single-day abs return on **adj** close &gt; threshold (default **50%**) without CA on that ex_date | **Flag** in DQ report; do not auto-delete; fail L1 only if `ingest.fail_on_outliers=true` (default **false**) |
| High &lt; low, close outside high/low | Hard-fail row |
| Volume &lt; 0 | Hard-fail row |

Rationale: Indian CA misfiles are common; human-fixable flags beat silent drops in V1.

---

## 12. Security identity lifecycle (ISIN)

1. **Canonical key = ISIN** everywhere in L0/L1.  
2. `symbol_isin_map` is SCD-lite: `valid_from` / `valid_to` for symbol changes.  
3. Mergers: `security_master` records `successor_isin` + `event_date`; price history does not auto-stitch across merger in V1 — **exclude merger window** from labels (Phase 1 already requires this).  
4. New listings: `listing_date` required before IPO&lt;6m exclusion can be enforced in universe phase; until `security_master` supplied, IPO exclusion is best-effort / skipped with warning.

**V1 proposal:** `security_master.csv` optional for first cleaning PR; **required** before universe exclusions that depend on listing date are enforced in production runs.

---

## 13. Point-in-time reconstruction

For research date T:

1. Use raw artifacts with `as_of_date/session_date <= T` and `downloaded_at` semantics from sidecars.  
2. Apply only CAs with `ex_date <= T` when building L1 as-of T (backward adj as of T’s known CA set).  
3. Universe membership / exclusions as-of T (already Phase 1).  
4. Persist `pit_as_of` in L1 run metadata when rebuilding historical panels.

**V1 practical mode:** Full L1 rebuild from all raw available (point-in-time approximate if user drops revised history). True bitemporal “as originally seen” remains available via immutable raw + sidecars for audit; default research path = **latest corrected clean rebuild** (reconfirmed from Phase 2).

---

## 14. Validation rules checklist (L1 publish)

Fail closed unless noted:

1. Schema version known  
2. Duplicate keys (§6)  
3. Checksum / lineage present  
4. Calendar present & covers panel range  
5. Missing sessions per §9  
6. CA rows for adjusting types have factors  
7. Structural OHLC invariants  
8. Row-count deviation vs prior L1 (config threshold)  

---

## 15. Implementation sequencing (after this ADR is approved)

Still **no features/labels/models**.

1. **PR-A (schema/lineage/calendar):** schema_version fields, duplicate-key specs in code, lineage columns, `trading_calendar` ingest, missing-session detector (may warn before full L1).  
2. **PR-B (CA adjustment):** L0 vs L1 layout, backward adjustment engine, fixture tests for split/bonus.  
3. **Stop** for architecture review of cleaning output.  
4. Only then Phase 6-oriented feature design (separate ADR).

If you prefer a single cleaning PR instead of A/B, say so at sign-off (default = **split A/B** for safer review).

---

## 16. Explicit non-goals

- Feature engineering / signals  
- Label generation / quantiles  
- Probabilities, ranking, backtests  
- NSE/broker downloaders  
- Total-return index with dividend reinvestment (deferred)  

---

## 17. Sign-off checklist

```text
§3 L0 vs L1 clean tiers: APPROVE / CHANGE: ...
§4 Schema versioning: APPROVE / CHANGE: ...
§5.1 CA types in/out of price adjust (div no-adjust): APPROVE / CHANGE: ...
§5.2 Backward-adjusted prices: APPROVE / CHANGE: ...
§6 Duplicate keys table: APPROVE / CHANGE: ...
§7 Lineage columns (row-level broadcast): APPROVE / CHANGE: ...
§8 Calendar required dataset: APPROVE / CHANGE: ...
§9 Missing sessions (hard-fail last N=5 days): APPROVE / CHANGE N=... / CHANGE policy: ...
§10–11 Missing/outlier policies: APPROVE / CHANGE: ...
§12 Security master optional then required for IPO rules: APPROVE / CHANGE: ...
§13 PIT = latest rebuild + immutable raw audit: APPROVE / CHANGE: ...
§15 Implement as PR-A then PR-B: APPROVE / single PR: ...
Phase 3 overall: APPROVE / HOLD
```

Give this file to your reviewer; return the filled checklist before any cleaning implementation starts.
