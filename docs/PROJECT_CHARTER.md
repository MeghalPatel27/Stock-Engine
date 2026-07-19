# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19
**Status:** Pre-implementation — Philosophy + Phase 1 finalized; Phase 0 proposal awaiting sign-off; no production code yet

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

### 2.2 System philosophy — **P3-leaning hybrid architecture for V1**, with **P2 (modular multi-signal + learned meta-ranking) as the deliberate long-term target**.

Three paradigms were compared (pure end-to-end ML, modular multi-signal, hybrid). Decision:

- **P1 (pure end-to-end ML): eliminated.** Data-hungry, opaque, poor fit for a narrow (~180–200 stock) universe with short per-field history.
- **P2 (modular multi-signal + learned meta-combiner): eliminated as a V1 *starting point***, retained as the target end-state. Too much upfront infra (OOF prediction storage, nested/walk-forward validation, signal registry, feature store) to justify before any signal is proven.
- **P3 (hybrid — rules/statistics/ML chosen per component): selected for V1.** Fastest path to a working, explainable, production-safe daily ranking without foreclosing the path to P2.

**V1 will be built as "P2 with the learned parts deferred,"** not as rules-forever. This is enforced by five non-negotiable invariants (see 2.3).

### 2.3 Non-negotiable invariants (locked in from V1, day one)
These exist specifically to prevent the hybrid approach from becoming a dead-end grab-bag:

1. **Signal contract** — every signal (rule, statistic, or model) emits a standardized schema: `{value, direction, confidence, timestamp, version}`. The combiner only ever consumes this contract, never a signal's internals.
2. **Point-in-time correctness** in data and features from day one (no lookahead leakage, ever).
3. **Pluggable combiner** — rule-based weighting and learned stacking are two interchangeable implementations behind one interface.
4. **Backtest harness from V1** that measures per-signal contribution (out-of-sample IC / predictive value), so we know which signals eventually deserve ML investment.
5. **Research/production code separation** from the start (`research/` vs `src/`).

**Related Phase 1 contract rule:** engine output fields are required; **do not** treat `p_bullish + p_bearish + p_neutral = 1` as an architectural invariant. Model implementations remain replaceable.

### 2.4 Technical debt V1 intentionally accepts
- Hand-set (not learned) signal combination weights.
- Heuristic, not calibrated, probability/risk/confidence outputs.
- Lightweight observability (no full per-signal monitoring platform yet).
- Feature layer as structured tables/parquet, not a full feature platform.
- Human-set rule priors may be imperfect (mitigated by backtesting every rule before shipping it).

**Debt explicitly refused (too costly to retrofit later):** no signal contract, no point-in-time correctness, no research/production separation. These are built correctly from day one.

### 2.5 Migration path: V1 → V2 (P3 → P2)
| Stage | Trigger | Action |
|---|---|---|
| Stage 1 | A signal shows stable out-of-sample IC in the backtest harness | Promote that signal from rule/stat to an ML submodel behind the same signal contract — no re-architecture needed |
| Stage 2 | Multiple signals proven + sufficient overlapping history | Build OOF prediction store + nested/walk-forward validation; replace hand-set weights with a learned meta-combiner |
| Stage 3 | Signal count grows | Add signal registry, full feature store, per-signal monitoring, regime as a gating layer, multi-horizon multi-task modeling |

### 2.6 Phase 1 — Problem formulation (finalized)
See [`docs/decisions/01-phase1.md`](decisions/01-phase1.md). Summary: cross-sectional outperform probability; ranking primary; close→close; 20/20/60 labels; weekly universe + configurable `adv_min` / `price_min`; Top 20 Longs/Shorts; 6-month paper trust gate with realistic costs.

---

## 3. Architecture Decision Roadmap (all phases identified so far)

- [x] **Philosophy** — P3-leaning hybrid for V1, P2 as target — [00-philosophy.md](decisions/00-philosophy.md)
- [x] **Phase 1 — Problem formulation** — [01-phase1.md](decisions/01-phase1.md)
- [~] **Phase 0 — Foundations & cross-cutting** — proposal awaiting sign-off — [02-phase0-proposal.md](decisions/02-phase0-proposal.md)
- [ ] **Phase 2 — Data sourcing & acquisition**: provider per data type, required history depth, daily data-availability timing, licensing/ToS constraints, vendor redundancy
- [ ] **Phase 3 — Data storage & schema**: storage paradigm per layer, raw/clean/feature boundaries, partitioning, bitemporal/point-in-time storage, versioning, symbol/ISIN mapping
- [ ] **Phase 4 — Ingestion pipeline, orchestration & data quality**: orchestration tooling, idempotency/backfill, trading calendar handling, data-quality gating, failure alerting
- [ ] **Phase 5 — Data cleaning & normalization**: corporate-action adjustment methodology, missing-data/halt handling, outlier detection, normalization conventions
- [ ] **Phase 6 — Feature engineering & feature store**: computation framework, feature category prioritization, leakage prevention, cross-sectional normalization, derivative-data (OI/rollover/expiry) handling, feature versioning
- [ ] **Phase 7 — Regime detection**: standalone model vs feature vs gating layer, regime definition/labeling, integration into ranking
- [ ] **Phase 8 — Modeling & training methodology**: baseline model family, single vs multi-horizon/multi-task, walk-forward validation protocol, non-stationarity/class imbalance handling, probability calibration, leakage controls
- [ ] **Phase 9 — Backtesting & validation**: backtest engine design, evaluation metrics, cost/slippage assumptions, robustness/significance testing
- [ ] **Phase 10 — Scoring, ranking & inference**: daily batch orchestration, model registry/versioning, multi-horizon reconciliation, risk/confidence integration, output storage/reproducibility
- [ ] **Phase 11 — Serving**: API surface, dashboard technology, auth/access model
- [ ] **Phase 12 — MLOps & production readiness**: experiment tracking, drift monitoring, retraining triggers, CI/CD, logging, cost management

---

## 4. Implementation Progress

**Status: 0% production code.** Architecture docs only — correct for this stage.

**Done:**
- Philosophy ADR
- Phase 1 ADR (finalized with sign-off amendments)
- Phase 0 architecture proposal written

**In progress:**
- Phase 0 sign-off — [`docs/decisions/02-phase0-proposal.md`](decisions/02-phase0-proposal.md)

**Not started:** Phase 2+, scaffolding (until Phase 0 approved), data, models.

---

## 5. What's Left

1. **Sign off Phase 0** (blocking).
2. Then either minimal scaffold (if approved in Phase 0 §15) or Phase 2 design first.
3. Phases 2 → 12 in order.

No phase should be skipped or batched ahead of schedule.

---

## 6. What's Needed From You

**Now:** Phase 0 sign-off checklist at the end of [`docs/decisions/02-phase0-proposal.md`](decisions/02-phase0-proposal.md).

Thereafter: explicit gate approval before each next phase; ADRs for every lock.

This document will be updated after each phase is finalized.
