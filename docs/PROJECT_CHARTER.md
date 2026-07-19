# Stock Intelligence Engine — Project Charter & Status

**Last updated:** 2026-07-19
**Status:** Pre-implementation — architecture philosophy finalized, no code built yet

---

## 1. Goals of the Engine

**Primary objective**
Every day, after Indian market close, analyze a curated universe of large-cap liquid F&O stocks and rank them by probability of outperforming in the near future.

**Output per stock (per run)**
- Bullish probability
- Bearish probability
- Risk score
- Confidence score
- Rank within the daily opportunity list

**Prediction horizons (tentative)**
- Next trading day
- 5 trading days
- 20 trading days

**What this system is NOT**
- Not HFT, not real-time / intraday trading
- No live exchange feed dependency
- Not built on illiquid, penny, or manipulated smallcap names

**Operating constraints**
- Data is mostly T-1 (end-of-day)
- Primarily free / publicly available Indian market data
- Built and maintained by a 1–2 person team
- Low budget
- Must be production-quality eventually, but must avoid premature overengineering in V1

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
5. **Research/production code separation** from the start.

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

---

## 3. Architecture Decision Roadmap (all phases identified so far)

This is the full ordered list of decision phases for the project. **Only Phase "Philosophy" above is finalized.** Everything below is identified but not yet decided.

- [x] **Philosophy** — P3-leaning hybrid for V1, P2 as target (finalized above)
- [ ] **Phase 0 — Foundations & cross-cutting**: language/runtime, local vs cloud, repo structure, environment/reproducibility, build-vs-buy posture
- [ ] **Phase 1 — Problem formulation, universe & success criteria**: target definition (absolute vs relative return), label construction per horizon, formal meaning of bullish/bearish/risk/confidence, benchmark for "outperform," exact universe definition & reselection, success metrics
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

**Status: 0% code/infrastructure built.** All work so far has been architectural decision-making. This is expected and correct at this stage — no premature building.

**Done:**
- Project goals, constraints, and non-goals defined
- Three architecture paradigms formally compared across 6 axes (small-team dev, Indian data availability, explainability, incremental iteration, production robustness, long-term scalability)
- V1 philosophy decided (hybrid/P3) with explicit rationale
- Technical debt accepted vs refused, explicitly enumerated
- Migration path from V1 to V2 (P2) defined with concrete triggers
- Five non-negotiable invariants locked in for all future implementation
- Full decision-phase roadmap identified and ordered

**Not started:** everything from Phase 0 onward — no tech stack chosen, no data source selected, no schema designed, no code written, no data pulled.

---

## 5. What's Left

Immediate next decision, in order:
1. **Phase 1 — Problem formulation** (recommended next): precise target definition, label construction, benchmark, universe rules, success metrics. This propagates into nearly every downstream layer, so it should be finalized before Phase 0 tech choices are locked, though a few Phase 0 questions (language/runtime) can be settled in parallel since they're low-risk.
2. **Phase 0 — Foundations**: stack, hosting, repo layout.
3. Then Phases 2 → 12 in order, one at a time, per the established working process (identify decisions → ask minimum clarifying questions → wait for answers → propose design → confirm before moving on).

No phase should be skipped or batched ahead of schedule.

---

## 6. What's Needed From You

Nothing is due immediately — the next step is that Claude will ask targeted clarifying questions for **Phase 1** (and then Phase 0) before proposing any design. In general, across the roadmap, you'll be asked to provide or decide:

- **Definitions:** what "outperform" means precisely (vs. index/sector/peers), what risk score and confidence score should represent
- **Universe rules:** exact large-cap F&O inclusion/exclusion criteria, rebalancing frequency
- **Data access:** which specific data sources/providers you already have or are willing to use (e.g., broker APIs, NSE bhavcopy, any paid data if budget allows for any single piece), and any subscriptions already in hand
- **Infra preferences:** local machine vs cloud, and any budget ceiling for compute/storage
- **Tech preferences:** any hard constraints on language/stack (or full delegation to Claude's recommendation)
- **Risk appetite / success bar:** what result would make V1 "good enough to trust," in your own terms
- **Time horizon priorities:** whether next-day, 5-day, or 20-day prediction matters most for V1, if we need to sequence them rather than build all three at once
- **Approval at each phase gate:** explicit sign-off before moving from one finalized phase to the next, per the collaboration rules

This document will be updated after each phase is finalized, so it always reflects the current source of truth for the project.
