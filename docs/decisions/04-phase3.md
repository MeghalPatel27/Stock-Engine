# ADR 04 — Phase 3: Data Cleaning, Normalization & Corporate Action Methodology

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [04-phase3-proposal.md](04-phase3-proposal.md)  
**Depends on:** [03-phase2.md](03-phase2.md), [03-ingest-review.md](03-ingest-review.md)

## Sign-off amendments

1. **Do not lock** “ordinary cash dividends never adjust.” Policy name: **price-return adjustment**.  
   - V1 price-return datasets **ignore** ordinary cash dividends.  
   - Future total-return datasets **may** include dividend adjustment — separate product, same CA table.  
2. Missing-session lookback **N** is configurable (default **5**).  
3. Implement as **PR-A then PR-B** (safer).  
4. Add a **machine-readable data dictionary** before feature engineering.  
5. Phase-3 end-state invariants: **deterministic rebuilds**, **immutable raw inputs**, **versioned outputs** (schema + dataset + config).  

## Locked decisions

| Topic | Decision |
|---|---|
| Tiers | **L0** normalized unadjusted; **L1** canonical research (CA price-return adjusted). Later phases consume **L1 only**. |
| Schema versioning | Every dataset has `schema_version` (≠ `dataset_version`) |
| Price adjustment | **Backward-adjusted**; retain raw + adjusted OHLC (and volume inverse on factor events) |
| Price-return CA in V1 | split/bonus/consolidation/rights(if factor)/demerger(if factor). **Not** ordinary cash dividends |
| Duplicate keys | See §Unique keys |
| Lineage | Row-level: source_file, raw_sha256, ingested_at, provider, schema_version, dataset_version, run_id |
| Calendar | Required `trading_calendar` — single source of truth |
| Missing sessions | Hard-fail gaps in last **N** trading days (default 5, configurable) for ISINs with prior history |
| Outliers | Flag extreme adj moves without CA; hard-fail only structural impossibilities |
| Security master | Optional until IPO rules enforced |
| PIT | Latest L1 rebuild + immutable raw audit trail |
| Sequencing | PR-A (schema/lineage/calendar/missing sessions/L0) → PR-B (L1 adjustment) → review → **not** features yet |

## Unique keys

| Dataset | Key |
|---|---|
| equity_eod | `(isin, session_date)` |
| corporate_actions | `(isin, ex_date, action_type)` |
| symbol_isin_map | `(isin, symbol, valid_from)` |
| trading_calendar | `(session_date)` |

## Phase-3 invariants

1. **Deterministic rebuilds** — same raw + config → identical L0/L1 outputs.  
2. **Immutable inputs** — raw never modified.  
3. **Versioned outputs** — every clean dataset traceable to schema_version, dataset_version, config_hash/config_version, run_id.  

## Data dictionary

Machine-readable definitions live under `docs/data/dictionary/*.yaml` (and stay aligned with code schemas). Required before feature engineering begins.

## Next after PR-A/PR-B review (roadmap addition)

**Feature Registry & Feature Store Design** (new design phase) **before** implementing indicators/labels. Not started until cleaning is reviewed.

## Explicit non-goals

No feature engineering, labels, probabilities, models, ranking, backtesting in this phase.
