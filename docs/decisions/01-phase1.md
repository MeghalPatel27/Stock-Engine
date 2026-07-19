# ADR 01 — Phase 1: Problem Formulation, Universe & Success Criteria

**Status:** Finalized  
**Date locked:** 2026-07-19  
**Supersedes:** [01-phase1-proposal.md](01-phase1-proposal.md) (proposal archive)  
**Depends on:** [00-philosophy.md](00-philosophy.md)

Changes vs original proposal (sign-off amendments):
1. `p_bullish + p_bearish + p_neutral = 1` is **not** an architectural invariant.
2. Liquidity / price thresholds are **configuration defaults**, not hardcoded constants.
3. Paper lists default to **Top 20** Longs and **Top 20** Shorts.

---

## 1. Context

Define what the Stock Intelligence Engine optimizes, how labels and scores are defined, which names are eligible, and what “V1 success” means — before any stack or data-provider lock.

---

## 2. Decision summary

| Topic | Locked decision |
|---|---|
| Objective | Probability of **cross-sectional outperformance** within the tradable F&O universe |
| Primary product | **Ranking** (Top Longs / Top Shorts); probs/risk/confidence support ranking |
| Benchmark | Universe cross-section — **not** Nifty 50 |
| Forward return | **Close(T) → Close(T+N)** |
| Labels | Top **20%** / Bottom **20%** / Middle **60%** (config defaults) |
| Horizons | **5d first**; 1d and 20d later as **separate** ranks (no blend in V1) |
| Universe | NSE F&O equities + **configurable** liquidity/price filters |
| Refresh | **Weekly** membership; **daily** hard exclusions |
| Use case | Always emit Top Longs **and** Top Shorts |
| Success | Own-capital comfort after **6 months paper**; risk-adjusted returns after realistic costs |
| Live path | Paper → tiny live capital |

---

## 3. Modeling objective (locked)

| Layer | Decision |
|---|---|
| Training / signal target | Cross-sectional probability of landing in top (long) or bottom (short) quantile of universe forward close-to-close return |
| Daily rank | Opportunity from directional scores; **risk and confidence modify** ranking / eligibility |
| Success evaluation | Risk-adjusted returns **after realistic trading costs** on Top Longs / Top Shorts paper portfolios (rank IC diagnostic only) |

**Not** the V1 training objective: raw expected-return regression; risk-adjusted return as the label itself.

---

## 4. Formal definitions

### 4.1 Forward return

```text
R_i(T, H) = Close_i(T+H) / Close_i(T) - 1
```

NSE trading-calendar days only. Missing `Close(T+H)` → exclude from that day’s label set (no imputation). Corporate-action adjustment method → Phase 5; returns must use adjusted closes once cleaning exists.

### 4.2 Cross-sectional labels (defaults; config-tunable)

Within eligible names with valid `R_i(T, H)`:

| Label | Default rule |
|---|---|
| Bullish | top `label_top_quantile` (default **0.20**) |
| Bearish | bottom `label_bottom_quantile` (default **0.20**) |
| Neutral | remainder (default **0.60**) |

Tie-breaking must be deterministic (document in Phase 8).

### 4.3 Engine output contract (per stock, per run, per horizon)

**Contract requires fields, not a specific probability generation method.**

| Field | Required | Semantics |
|---|---|---|
| `p_bullish` | Yes | Score in [0,1] interpreting bullish / top-quantile opportunity (model-defined) |
| `p_bearish` | Yes | Score in [0,1] interpreting bearish / bottom-quantile opportunity |
| `p_neutral` | Optional | Present when the model emits an explicit neutral mass; **not required** of all models |
| `risk` | Yes | Composite risk in [0,1]; higher = worse |
| `confidence` | Yes | Composite trust in [0,1]; **not** directional probability |
| `rank_long` | Yes | 1 = strongest long opportunity among eligible that run |
| `rank_short` | Yes | 1 = strongest short opportunity among eligible that run |

#### Non-invariant (explicit)

Do **not** permanently enforce:

```text
p_bullish + p_bearish + p_neutral = 1
```

That may be true for some probabilistic classifiers; ranking, regression, or ensemble heads may not. Downstream consumers must not assume the sum constraint. If a given model chooses a simplex parameterization, that is a **model implementation detail**, versioned with that model — not an engine-wide invariant.

#### Horizon outputs

| Horizon | V1 status |
|---|---|
| 5d | Primary — build first (`Rank_5D_Long` / `Rank_5D_Short` + supporting fields) |
| 1d | Later, separate ranks |
| 20d | Later, separate ranks |

No blended multi-horizon rank in V1.

### 4.4 Risk (composite components locked; weights later)

Must include: downside volatility, drawdown tendency, prediction uncertainty, liquidity, event exposure. Never volatility-only. Weights → Phase 10.

### 4.5 Confidence (composite components locked)

Must include: model agreement, signal agreement, regime familiarity, data quality. Not equal to `max(p_bullish, p_bearish)`.

---

## 5. Universe

### 5.1 Inclusion
NSE F&O equity underlyings ∩ configurable liquidity/price filters ∩ not excluded.

### 5.2 Configurable thresholds (defaults — not hardcoded constants)

| Config key | Default | Notes |
|---|---|---|
| `adv_min` | ₹50 crore (20-session median) | Tunable after Phase 2 data analysis |
| `price_min` | ₹50 | Configurable |
| `label_top_quantile` | 0.20 | |
| `label_bottom_quantile` | 0.20 | |
| `top_n_longs` | 20 | Published Top Longs list size |
| `top_n_shorts` | 20 | Published Top Shorts list size |

Delivery % is **not** a membership filter; feature / risk signal only.

All liquidity, price floors, exclusion toggles, and quantiles live in **configuration** (see Phase 0 config system). Changing a threshold requires config/version bump — not a code fork.

### 5.3 Refresh
- **Weekly** universe membership recompute  
- **Daily** application of hard exclusions even inside a membership week  

### 5.4 Hard exclusions (daily)
ASM/GSM, F&O ban, IPO &lt; 6 months, halted securities, merger periods, major corporate actions.

### 5.5 Point-in-time
Membership and exclusions as-of decision date T only (philosophy invariant #2).

---

## 6. Success criteria & capital path

**Trust gate (authoritative):**  
> I would deploy a small amount of my own capital after six successful months of paper trading.

Supporting diagnostics (not substitutes): risk-adjusted Top-20 Long / Top-20 Short performance after realistic brokerage and slippage vs baselines; rank IC; cross-regime stability.

**Costs:** realistic broker/slippage assumptions required for decision-grade evaluation (schedule → Phase 9).

**Path:** paper only → then tiny live capital. No meaningful capital on first live day.

---

## 7. Consequences

- Phase 2+ data, features, models, and backtests must align to cross-sectional outperform probability + separate long/short ranks.  
- Provider and model swaps must honor the **output contract** without assuming simplex probabilities.  
- Thresholds are config-driven so Phase 2 analysis can retune without redesign.  
- Next gate: **Phase 0 architecture proposal** (not implementation, not Phase 2).

---

## 8. Sign-off record

Signed off 2026-07-19 from answer pack (`docs/QUESTIONS.md`) with Q2/Q7 amendments as above.
