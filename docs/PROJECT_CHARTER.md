# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19
**Status:** Phase 0 scaffold complete; Philosophy + Phase 1 + Phase 0 finalized; Phase 2 design proposed (awaiting sign-off); no market-data ingestion yet

---

## 1. Goals of the Engine

**Primary objective**
Every day, after Indian market close, analyze a curated universe of liquid F&O stocks and **rank** them by probability of **cross-sectional outperformance** within that universe (not vs Nifty 50).

**Output per stock (per run, per horizon)**
- `p_bullish`, `p_bearish`, optional `p_neutral`
- Risk score, confidence score (confidence ≠ directional probability)
- `rank_long`, `rank_short`
- Published lists: Top 20 Longs, Top 20 Shorts (config defaults)

**Prediction horizons**
- **V1 primary:** 5 trading days
- Later (separate ranks, no blend): 1 day, 20 days

**What this system is NOT**
- Not HFT, not real-time / intraday trading
- No live exchange feed dependency
- Not built on illiquid, penny, or manipulated smallcap names
- Not an index-forecasting engine

**Operating constraints**
- Data is mostly T-1 (end-of-day)
- Prefer free / publicly available Indian market data; ≤ ₹2–5k/month if paid tools needed
- Built and maintained by a 1–2 person team
- Local-first; cloud later only if necessary
- Production-quality eventually, but avoid premature overengineering in V1

**High-level workflow**
```
Data Collection → Data Cleaning → Feature Engineering → Regime Detection
→ Model Inference → Ranking Engine → Dashboard / API
```

---

## 2. Finalized Decisions (as of today)

### 2.1 Collaboration model
- Claude acts as technical cofounder / principal engineer.
- No architectural, technology, or schema decisions are made unilaterally — ambiguity is always surfaced as a question before proceeding.
- Work proceeds one layer at a time; each layer is finalized before moving to the next.
- Bad or suboptimal proposals are challenged with tradeoffs, not silently implemented.
- Every finalized decision is recorded as an **ADR** under `docs/decisions/`.
- Delivery branch convention for this project: push finalized work to **`main`**.

### 2.2–2.5 Philosophy
See [`docs/decisions/00-philosophy.md`](decisions/00-philosophy.md) — P3 hybrid V1 → P2 target; five invariants including signal contract, PIT correctness, pluggable combiner, backtest harness, research/production separation.

### 2.6 Phase 1 — Problem formulation (finalized)
[`docs/decisions/01-phase1.md`](decisions/01-phase1.md)

### 2.7 Phase 0 — Foundations (finalized)
[`docs/decisions/02-phase0.md`](decisions/02-phase0.md) — Python 3.11+, uv, monorepo with `scripts/` + `data/metadata/`, Pydantic contracts including `RunMetadata`, config hash on every run, Ruff + pytest + GHA CI.

---

## 3. Architecture Decision Roadmap

- [x] **Philosophy** — [00-philosophy.md](decisions/00-philosophy.md)
- [x] **Phase 1 — Problem formulation** — [01-phase1.md](decisions/01-phase1.md)
- [x] **Phase 0 — Foundations** — [02-phase0.md](decisions/02-phase0.md) + minimal scaffold on `main`
- [~] **Phase 2 — Data sourcing & acquisition** — proposal awaiting sign-off — [03-phase2-proposal.md](decisions/03-phase2-proposal.md)
- [ ] **Phase 3 — Data storage & schema** (detail beyond Phase 2 storage sketch)
- [ ] **Phase 4 — Ingestion pipeline, orchestration & data quality**
- [ ] **Phase 5 — Data cleaning & normalization**
- [ ] **Phase 6 — Feature engineering & feature store**
- [ ] **Phase 7 — Regime detection**
- [ ] **Phase 8 — Modeling & training methodology**
- [ ] **Phase 9 — Backtesting & validation**
- [ ] **Phase 10 — Scoring, ranking & inference**
- [ ] **Phase 11 — Serving**
- [ ] **Phase 12 — MLOps & production readiness**

---

## 4. Implementation Progress

**Scaffold only (no business/ingestion logic):** package layout, contracts, config loader, logging bootstrap, tests, CI, scripts.

**In progress:** Phase 2 sign-off.

**Blocked until Phase 2 APPROVE:** market-data ingestion, modeling.

---

## 5. What's Left

1. Sign off Phase 2 design.  
2. Then first narrow ingestion implementation PR (protocol + one official adapter) if P2-Q7 approved.  
3. Phases 3+ in order.

---

## 6. What's Needed From You

**Now:** Phase 2 sign-off checklist in [`docs/decisions/03-phase2-proposal.md`](decisions/03-phase2-proposal.md).
