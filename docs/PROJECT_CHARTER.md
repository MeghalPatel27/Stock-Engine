# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19  
**Status:** Philosophy + Phase 1 + Phase 0 + Phase 2 finalized; local CSV ingest foundation implemented; **stopped before features/labels/models**

---

## Goals (short)

Rank liquid NSE F&O stocks daily (post-close) by probability of cross-sectional outperformance over ~5 trading days. Top 20 Longs / Top 20 Shorts. Paper 6 months before tiny live capital.

---

## Finalized ADRs

| ADR | Doc |
|---|---|
| 00 Philosophy | [decisions/00-philosophy.md](decisions/00-philosophy.md) |
| 01 Problem formulation | [decisions/01-phase1.md](decisions/01-phase1.md) |
| 02 Foundations | [decisions/02-phase0.md](decisions/02-phase0.md) |
| 03 Data acquisition | [decisions/03-phase2.md](decisions/03-phase2.md) |

### Phase 2 V1 acquisition note
No external NSE/broker downloaders in V1. User drops CSVs into `data/incoming/`. `DataSource` protocol allows future adapters without changing clean/raw/metadata pipeline. Corporate actions **mandatory**. Canonical id = **ISIN**. Clean = **Parquet only**.

---

## Roadmap

- [x] Philosophy, Phase 1, Phase 0, Phase 2 (design + narrow ingest impl)
- [ ] Phase 3+ (storage detail, cleaning methodology, features, models, …) — **design review before feature/label work**

---

## What's needed from you

Review the ingest foundation. Approve before any feature engineering or labeling phase begins.
