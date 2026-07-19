# ADR 03 — Phase 2: Data Acquisition Design (Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [01-phase1.md](01-phase1.md), [02-phase0.md](02-phase0.md)  

**Hard rule:** No market-data ingestion or modeling code until this ADR is finalized.

This document evaluates EOD data needs, candidate sources, point-in-time strategy, storage layout, and ingestion design — then recommends a V1 approach for sign-off.

---

## 1. Context

Phase 1 locked a cross-sectional ranking engine over liquid NSE F&O equities (5d primary). Phase 0 locked local-first Python scaffolding. We now must choose **how data enters the system** without locking forever to one vendor (provider abstraction).

Budget: prefer free/official; ≤ ₹2–5k/month if a paid piece clearly saves weeks.

---

## 2. Data requirements (from Phase 1 — what, not who)

### 2.1 Must-have for V1 labels, universe, ranks

| Domain | Fields / artifacts | Used for |
|---|---|---|
| Equity EOD bars | OHLCV, traded value, symbol, session date | Returns, ADV, features |
| Adjustments | Adjusted close **or** raw + corporate-action table | Fair close→close returns |
| Calendar | NSE trading sessions | Horizon T+N trading days |
| F&O membership | Underlying list **as-of history** | Universe inclusion |
| Listing metadata | Listing / relist date | IPO &lt; 6 months exclusion |
| Exclusions | F&O ban, ASM/GSM, halts, merger/major CA windows | Daily eligibility |

### 2.2 Strongly needed soon (risk / features)

| Domain | Why |
|---|---|
| Delivery % | Feature / risk (not membership) |
| Earnings / results calendar | Event risk |
| Major CA schedule | Exclusion windows + event risk |

### 2.3 Deferred (post-V1 enrichment)

F&O derivatives (OI, PCR, rollover, basis), fundamentals, shareholding, news/sentiment.

### 2.4 History depth (proposed default)

| Series | Proposed minimum | Rationale |
|---|---|---|
| Equity EOD | **≥ 5 years** trading days where available | Walk-forward + regime diversity |
| F&O membership history | Same span or best effort + documented gaps | Point-in-time universe |
| Exclusion lists | Best available; document start dates | Avoid silent bias |

---

## 3. Provider evaluation axes

Every candidate scored on:

1. **Point-in-time correctness** — can we reconstruct “what was knowable after close on day T”?  
2. **Reliability / uptime** of daily availability after NSE close  
3. **Maintainability** for 1–2 person team (parse fragility, auth, breaking changes)  
4. **Legal / ToS** fitness for research + eventual small live use  
5. **Cost** within ₹0–5k/month  
6. **Coverage** of must-have domains above  

---

## 4. Candidate sources (evaluation)

> Status as of design time — verify ToS and current endpoints before implementation.

| Source | Pros | Cons | Fit |
|---|---|---|---|
| **NSE official artifacts** (bhavcopy / reports / circulars) | Authoritative, free, aligns with “official preferred” | Format/URL churn; some histories awkward; scrape/download fragility; membership/ban may need multiple reports | **Primary candidate for EOD equity + many official lists** |
| **Broker historical APIs** (Zerodha/Upstox/Fyers/etc.) | Cleaner APIs, adjusted series often easier | Needs account; rate limits; ToS for redistribution/storage; may lack full PIT membership/ban history | **Strong secondary / adjusted-price complement** once an account exists |
| **Yahoo / generic global scrapers** | Easy | Weak India corporate-action quality; ToS/reliability poor for production | **Reject as primary** |
| **Paid India vendors** (e.g. specialized NSE feeds) | Convenience, history, corp actions | Cost; still need PIT discipline; vendor lock | **Only if free path fails history/PIT bar** within budget |

### Recommendation (proposed)

**V1 acquisition architecture: official-first, broker-optional complement, paid last resort.**

| Domain | Proposed primary | Fallback |
|---|---|---|
| Equity EOD OHLCV + traded value | NSE equity bhavcopy (or successor official daily file) | Broker history API for backfill gaps / adjusted closes |
| Corporate actions | Official CA reports + verify against adjusted series | Broker adjusted close as cross-check |
| Trading calendar | Derive from observed sessions + NSE holiday list | Static holiday file maintained in-repo |
| F&O underlying membership | Official F&O list / contract reports (versioned snapshots) | Manual curated snapshot only as emergency |
| Ban / ASM / GSM | Official circulars / ban lists snapped daily | — |
| Halts | Official or infer from OHLC/volume anomaly + halt reports if available | Conservative exclude on unresolved halt |
| Delivery % | Official delivery data if free series exists | Defer feature until available |
| Earnings calendar | Free public calendar provider TBD in implementation spike | Manual CSV in `data/metadata` short-term |

Exact URLs/libraries are **implementation details after approval** — not locked here.

---

## 5. Provider abstraction (required)

```text
MarketDataProvider (protocol)
  list_sessions(start, end) -> …
  get_equity_eod(symbols|universe, start, end, as_of) -> …
  get_corporate_actions(...)
  get_fno_members(as_of)
  get_exclusions(as_of)  # ban, asm/gsm, halt, …
```

- `src/stock_engine` depends on the **protocol + normalized schemas**, never on a vendor SDK in feature/rank code.  
- Vendor adapters live behind the protocol (e.g. `adapters/nse_official.py`, `adapters/broker_x.py`).  
- Swapping providers must not change RankRow / Signal / RunMetadata contracts.

---

## 6. Point-in-time correctness

### 6.1 Principles

1. Every raw download is stored with `downloaded_at` (wall clock) and intended `session_date` / `as_of_date`.  
2. Features and universe for decision date **T** may use only data with `available_at <= decision_time(T)` (post-close batch → typically “after T close”).  
3. **No** future membership: stock added to F&O next month must not appear in historical universe before listing-as-F&O date.  
4. Restatements: if a vendor revises history, keep prior raw bytes immutable; new pull = new version; document whether research uses “as originally seen” vs “latest corrected” (V1 default proposal: **immutable raw + latest clean rebuild**, with raw archive for audit).

### 6.2 Decision time convention (aligns Phase 1)

Daily batch assumes ranking runs **after** session T close when T’s official files are available. If files arrive late, run either waits or marks `as_of_date` incomplete in RunMetadata / pipeline state — **no silent use of T+1 open data for T decisions**.

---

## 7. Storage architecture (local-first V1)

Aligned with Phase 0 layout:

```text
data/
  raw/           # immutable vendor payloads (by provider, date, version)
  clean/         # normalized tables (parquet/csv) — still no lookahead columns
  features/      # Phase 6+; empty for now
  metadata/
    manifests/   # what was downloaded, row counts, checksums
    datasets/    # dataset_version descriptors
    runs/        # RunMetadata JSON per run
    pipeline/    # stage success/failure state
```

| Layer | Format (proposed) | Partitioning |
|---|---|---|
| raw | Original file bytes + small JSON sidecar | `provider/dataset/session_date/…` |
| clean | Parquet preferred (CSV acceptable early) | `table/session_date=…` or `table/year=…` |
| metadata | JSON | by `run_id` / `dataset_version` |

**Not in V1:** cloud warehouse, Kafka, full feature store product.

Symbol identity: V1 keys on **NSE trading symbol** + map table stub for ISIN when available (full ISIN discipline can deepen in Phase 3).

---

## 8. Ingestion strategy (design only — do not implement yet)

### 8.1 Daily happy path (after close)

1. Create `run_id` + RunMetadata skeleton (`config_hash`, `config_version`, `as_of_date=T`).  
2. Fetch/store **raw** artifacts for session T (idempotent: checksum skip if unchanged).  
3. Validate freshness / schema gate (fail closed → no clean publish).  
4. Build **clean** equity EOD + membership + exclusions snapshots.  
5. Write manifests under `data/metadata/`.  
6. Stop before features/models until later phases approved.

### 8.2 Backfill

- Explicit CLI/script later under `scripts/` or package entrypoint — **idempotent**, date-range bounded.  
- Backfill must not overwrite raw history; append versions.

### 8.3 Idempotency & DQ (preview for Phase 4)

- Re-running same `as_of_date` with same raw checksums = no-op clean.  
- Gates: row-count floors, null close checks, duplicate symbol checks, calendar alignment.  

Detailed orchestration tooling choice → Phase 4 ADR (V1 can be cron + CLI).

---

## 9. Licensing / ToS posture (proposed policy)

1. Prefer sources that allow local research storage of EOD history.  
2. Do not redistribute vendor bulk data outside the project.  
3. Document each adapter’s ToS notes under `docs/data/providers.md` when implemented.  
4. If a broker API ToS forbids the intended use, demote to non-primary.

---

## 10. Explicit non-goals for Phase 2 implementation (when approved)

- No live/websocket feeds  
- No intraday bars for V1  
- No modeling / ranking computation in the ingestion PR  
- No paid vendor commit without a short cost justification ADR note  

---

## 11. Open items to confirm at sign-off

| ID | Question | Options / default |
|---|---|---|
| P2-Q1 | Accept **official-first + broker complement** recommendation? | APPROVE / CHANGE |
| P2-Q2 | History depth **≥ 5 years** where available? | APPROVE / CHANGE to N years |
| P2-Q3 | Raw immutability + rebuildable clean layer? | APPROVE / CHANGE |
| P2-Q4 | Clean format **Parquet** (CSV OK for tiny fixtures)? | APPROVE / CHANGE |
| P2-Q5 | Defer delivery % & earnings until a free reliable series is found? | APPROVE / require in V1 MVP |
| P2-Q6 | Symbol key = NSE ticker V1, ISIN map best-effort? | APPROVE / CHANGE |
| P2-Q7 | After this ADR finalizes, first implementation PR = **provider protocol + one official EOD adapter + raw/clean write for one table** (still no features/models)? | APPROVE / narrower / broader |

---

## 12. Sign-off checklist

```text
§2 Data requirements list: APPROVE / CHANGE: ...
§4 Official-first recommendation: APPROVE / CHANGE: ...
§5 Provider protocol abstraction: APPROVE / CHANGE: ...
§6 Point-in-time rules: APPROVE / CHANGE: ...
§7 Storage layout (raw/clean/features/metadata): APPROVE / CHANGE: ...
§8 Ingestion strategy (design): APPROVE / CHANGE: ...
§9 ToS posture: APPROVE / CHANGE: ...
P2-Q1 … P2-Q7: (answers)
Phase 2 overall: APPROVE → allow first ingestion scaffold PR / HOLD
```

Until **Phase 2 overall: APPROVE**, no ingestion implementation beyond empty folders already scaffolded.
