# ADR 03 — Phase 2: Data Acquisition

**Status:** Finalized (ingest implementation **approved** in review)  
**Date locked:** 2026-07-19  
**Review:** [03-ingest-review.md](03-ingest-review.md) — APPROVE; follow-ups R1–R5 → Phase 3  
**Supersedes:** [03-phase2-proposal.md](03-phase2-proposal.md)  
**Depends on:** [01-phase1.md](01-phase1.md), [02-phase0.md](02-phase0.md)

## Sign-off amendments (locked)

1. **Corporate actions are mandatory** for Phase 2 / V1 ingestion — not optional, not deferred.  
2. Official-first strategy retained as the **long-term** acquisition posture; broker secondary; paid last resort.  
3. **Canonical security id = ISIN**; trading symbol is display/secondary; maintain symbol↔ISIN map; providers return normalized ids.  
4. Every raw archive stores **SHA-256** + `downloaded_at`, `session_date`, `provider`, `dataset_version`; raw immutable forever.  
5. Clean datasets are **Parquet only** (CSV only under `tests/` fixtures).  
6. **DQ gates mandatory** before publishing clean (duplicates, missing closes, row-count deviation, invalid dates, checksum) — fail closed.  
7. Delivery % and earnings calendar may be deferred; corporate actions may not.  
8. First implementation PR scope: protocol + source adapter + raw + clean + metadata + validation — **no features/labels/models**.  

### Additional V1 project decision (overrides “implement NSE adapter now”)

For V1 development: **do not implement** external downloaders, broker APIs, HTTP clients, scraping, auth, scheduled downloads, or cloud storage.

Assume the user **manually drops CSV files** into a fixed incoming directory. The pipeline is provider-agnostic via a `DataSource` interface so official/broker adapters can populate the same incoming contract later **without changing downstream code**.

```text
data/
  incoming/    # user (or future downloader) drops CSV here
  raw/         # immutable archived copies + checksum sidecars
  clean/       # normalized Parquet only
  metadata/    # manifests, run metadata, dataset versions, pipeline state
  features/    # reserved; unused until later phases
```

---

## 1. Context

Acquire and normalize market data needed for Phase 1 ranking, with point-in-time correctness and swappable sources — starting from local CSV drops.

---

## 2. Data requirements (locked)

### Mandatory now

| Domain | Role |
|---|---|
| Equity EOD OHLCV (+ traded value when available) | Returns, ADV, features later |
| **Corporate actions** | Correct historical returns / adjustments |
| Trading calendar | Horizon T+N (derivable from sessions + holiday list later) |
| F&O membership (as-of) | Universe |
| Listing dates | IPO &lt; 6 months exclusion |
| Exclusions (ban, ASM/GSM, halt, merger/major CA windows) | Daily eligibility |
| Symbol ↔ ISIN mapping | Canonical identity |

### Deferred allowed

Delivery %, earnings calendar, derivatives OI, fundamentals, news.

### History

≥ **5 years** where available; longer preferred.

---

## 3. Long-term source strategy vs V1 implementation

| Horizon | Decision |
|---|---|
| Long-term | Official-first → broker complement → paid only if free path fails |
| **V1 now** | `LocalIncomingCsvSource` only — reads `data/incoming/` |
| Future | Adapters that fetch NSE/broker and **write into `incoming/`** (or emit the same artifact interface); clean pipeline unchanged |

---

## 4. DataSource protocol (locked)

Provider-agnostic. Downstream never imports vendor SDKs.

Responsibilities:

- List available artifacts for an `as_of_date` / run  
- Provide bytes (or path) for each artifact  
- Declare `provider` id (e.g. `local_csv`, later `nse_official`)  
- Emit **normalized identifiers** (ISIN required when available in the file; symbol secondary)

V1 concrete implementation: **`local_csv`** scanning `data/incoming/`.

---

## 5. Point-in-time & raw immutability (locked)

Every raw object stores sidecar metadata:

- `sha256`
- `downloaded_at` (ingestion wall clock)
- `session_date` / `as_of_date`
- `provider`
- `dataset_version`
- original filename / content type

Raw files are **immutable forever** (never overwrite; new content = new versioned object).

Clean layer is rebuildable from raw.

---

## 6. Storage (locked)

| Layer | Format | Notes |
|---|---|---|
| incoming | CSV (user-supplied) | Staging only; not the system of record |
| raw | Original bytes + JSON sidecar | Immutable |
| clean | **Parquet only** | Production datasets |
| metadata | JSON | RunMetadata, manifests, DQ reports |
| features | (reserved) | Empty until Phase 6 |

CSV is allowed **only** for `tests/**/fixtures`.

---

## 7. Data quality gates (locked — fail closed)

Before publishing any clean dataset:

1. Checksum verification vs sidecar  
2. Duplicate symbol/ISIN+date keys  
3. Missing close prices (equity EOD)  
4. Invalid / non-session dates  
5. Row-count deviation vs threshold / prior (when baseline exists)  

Failure → do not write clean publish; record failure in metadata/pipeline state.

---

## 8. First implementation scope (this PR)

Implement only:

1. `DataSource` protocol  
2. `LocalIncomingCsvSource`  
3. Immutable raw archive + SHA-256 sidecars  
4. Normalize equity EOD + corporate actions (+ symbol map) → clean Parquet  
5. RunMetadata + manifests + dataset_version  
6. DQ validation gates  

**Stop.** No features, labels, models, NSE/broker connectors.

---

## 9. Sign-off record

Phase 2 overall **APPROVE** (2026-07-19) with amendments and V1 local-CSV decision above.
