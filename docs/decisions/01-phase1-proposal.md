# Phase 1 — Problem Formulation (Design Proposal)

**Status:** Proposed — awaiting explicit sign-off  
**Date:** 2026-07-19  
**Depends on:** [00-philosophy.md](00-philosophy.md)  
**Answers source:** user Phase 1 reply (2026-07-19)

This document locks problem definition for V1. **No Phase 2 (data) or Phase 0 (foundations) lock until this is signed off.** Soft Phase 0 preferences are recorded but non-binding.

---

## 1. Locked answers (verbatim mapping)

| ID | Decision |
|---|---|
| A1 | Outperform **within the F&O tradable universe cross-section** (not Nifty 50) |
| A2 | **Ranking is primary**; bullish/bearish/confidence/risk are supporting outputs; portfolio built from rank |
| A3 | Label / eval window: **Close(T) → Close(T+N)** |
| B1 | Labels: **top/bottom quantiles** (default 20% / 20%; middle = neutral) |
| B2 | Risk: **composite** (downside vol, drawdown tendency, prediction uncertainty, liquidity, event exposure) |
| B3 | Confidence: **composite** (model agreement, signal agreement, regime familiarity, data quality) — **not** a probability |
| B4 | Bullish + Bearish **≠ 1**; allow **Neutral** mass (three-way) |
| C1 | V1 horizon priority: **5 trading days first** |
| C2 | Multi-horizon: **separate ranks** (no blending in V1) |
| D1 | Universe: **F&O equities + liquidity filters** |
| D2 | Universe refresh: **weekly** |
| D3 | Exclusions: ASM/GSM, F&O ban, IPO &lt;6 months, halted, merger periods, major corporate actions |
| D4 | Use case: **long and short** (Top Longs + Top Shorts; shorts ignorable by user) |
| E1 | Success: comfortable allocating **small own capital after 6 months successful paper trading**; risk-adjusted returns after realistic costs |
| E2 | Costs: **include realistic broker costs** in evaluation |
| E3 | Live path: **6 months paper → very small live capital** |
| F1–F4 | Soft prefs only (see §8) |

---

## 2. Foundational modeling objective (user-flagged gap)

### Question
Should the engine optimize for **expected return**, **risk-adjusted return**, or **probability of outperforming**?

These imply different labels, losses, metrics, and architectures.

### Recommendation for V1 — **probability of outperforming (cross-sectional), with risk-aware ranking and risk-adjusted evaluation**

| Layer | V1 choice | Why |
|---|---|---|
| **Training / signal target** | Cross-sectional **probability of landing in top (long) or bottom (short) quantile** of universe forward close-to-close return | Matches A1/A2/B1; ranking engine, not index or return-regression engine |
| **Daily rank construction** | Sort primarily by opportunity score derived from P(top) / P(bottom); **risk and confidence adjust rank / eligibility**, not replace the target | Keeps explainable separation of “edge” vs “danger” vs “trust” |
| **Success evaluation** | **Risk-adjusted returns after realistic costs** on Top Longs / Top Shorts paper portfolios (plus rank IC as diagnostic) | Matches E1/E2 without forcing a fragile risk-adjusted *training* label in V1 |

### Alternatives rejected for V1 (kept as later options)

| Alternative | Tradeoff |
|---|---|
| **Expected-return regression** | Natural for continuous PnL; worse fit for “Top Longs / Top Shorts” product; more sensitive to outliers and non-stationarity in Indian F&O names |
| **Risk-adjusted return as training label** (e.g. forward Sharpe-like, return/σ) | Aligns with E1 intuitively, but labels are noisier, require stable risk estimates inside the label (lookahead-prone if done badly), and conflate edge with risk before we have a proven risk model |
| **Pure probability without risk in ranking** | Violates B2 intent and E1; high-prob volatile names would dominate |

### V1 rank recipe (conceptual — combiner details in Phase 10)

For each horizon `H` independently:

1. Compute `P_bull`, `P_bear`, `P_neutral` with `P_bull + P_bear + P_neutral = 1`
2. Long opportunity score ≈ `f(P_bull, confidence)` with risk penalty / gate  
3. Short opportunity score ≈ `f(P_bear, confidence)` with risk penalty / gate  
4. Emit `Rank_{H}_Long` and `Rank_{H}_Short` (plus supporting fields)

Exact `f` and risk penalty form are **Phase 10**; Phase 1 only locks that **target = cross-sectional outperform probability**, not raw expected return.

**Sign-off checkpoint:** Approve or reject §2 before Phase 1 is considered finalized.

---

## 3. Formal definitions

### 3.1 Universe membership (point-in-time)

On each **universe refresh** (weekly, see §5):

**Eligible** iff all of:

1. Equity is an NSE F&O underlying (as of refresh as-of date)
2. Passes liquidity filters (§5 — proposed thresholds)
3. Not in exclusion set (§5)

Membership used for day `T` features/labels/ranking is the **last completed weekly snapshot as of T** (point-in-time; no future membership leakage).

### 3.2 Forward return (label input)

For horizon `H` trading days:

```text
R_i(T, H) = Close_i(T+H) / Close_i(T) - 1
```

- Trading calendar: NSE equity sessions only  
- If `Close(T+H)` unavailable (delist, halt through horizon): **exclude from that day’s label set** (not imputed)  
- Corporate-action adjustment methodology deferred to Phase 5; Phase 1 requires **adjusted closes for return construction** once cleaning exists  

### 3.3 Cross-sectional labels (per day T, per horizon H)

Within the eligible universe that has a valid `R_i(T, H)`:

| Label | Rule (V1 default) |
|---|---|
| Bullish | `R_i` in **top 20%** of that day’s cross-section |
| Bearish | `R_i` in **bottom 20%** |
| Neutral | middle **60%** |

Ties at quantile boundaries: assign by stable sort on `(return desc, symbol asc)` then cut at floor(0.2N) / ceil(0.8N) — exact tie rule can be refined in Phase 8; must be deterministic and documented.

**Note:** Labels are for training/evaluation of directional modules. The **product** still emits continuous probabilities + ranks every day.

### 3.4 Output schema (per stock, per run, per horizon)

| Field | Type | Semantics |
|---|---|---|
| `p_bullish` | float [0,1] | Prob. of top-quantile outcome |
| `p_bearish` | float [0,1] | Prob. of bottom-quantile outcome |
| `p_neutral` | float [0,1] | Prob. of middle outcome |
| Constraint | — | `p_bullish + p_bearish + p_neutral = 1` |
| `risk` | float [0,1] | Composite risk (§3.5); higher = worse |
| `confidence` | float [0,1] | Composite confidence (§3.6); higher = more trust; **not** a probability of direction |
| `rank_long` | int 1..N | Lower = stronger long opportunity |
| `rank_short` | int 1..N | Lower = stronger short opportunity |

Horizons in V1 sequencing:

| Horizon | V1 status | Output names |
|---|---|---|
| 5d | **Primary — build first** | `Rank_5D_Long`, `Rank_5D_Short`, probs/risk/confidence for 5d |
| 1d | Deferred after 5d pipeline works | `Rank_1D_*` |
| 20d | Deferred after 5d pipeline works | `Rank_20D_*` |

No blended multi-horizon rank in V1.

### 3.5 Risk score (composite — components locked; weights Phase 10)

Must include (not vol-only):

1. Downside volatility  
2. Drawdown tendency  
3. Prediction uncertainty  
4. Liquidity risk  
5. Event exposure (earnings, major CA, ban proximity, etc.)

V1: heuristic weighted composite behind the signal/score contract. Calibration deferred (charter debt).

### 3.6 Confidence score (composite)

Must include:

1. Model agreement (when multiple models exist; V1 may be single-path → weight near-neutral)  
2. Signal agreement  
3. Regime familiarity  
4. Data quality / completeness for that name-day  

Explicitly **not** equal to `max(p_bullish, p_bearish)`.

---

## 4. Daily product shape

After market close, for the active horizon(s):

1. Score all eligible names  
2. Publish **Top Longs** (best `rank_long`)  
3. Publish **Top Shorts** (best `rank_short`)  
4. Full universe table with all fields for audit / later portfolio construction  

Users may ignore shorts; engine always produces both.

---

## 5. Universe rules (V1)

### 5.1 Inclusion base
NSE F&O equity underlyings ∩ liquidity filters ∩ not excluded.

### 5.2 Liquidity filters — **proposed defaults (sign-off required)**

Exact numbers were not specified; proposed starting gates (tunable, versioned):

| Filter | Proposed V1 default | Rationale |
|---|---|---|
| Average daily traded value (ADV) | ≥ ₹50 crore (20-session median) | Large-cap liquid F&O; avoids thin names |
| Price floor | ≥ ₹50 | Reduces penny-like microstructure noise |
| Delivery % | **monitor, not hard-gate in V1** | Useful signal later; unstable as hard filter |
| Turnover / impact | Prefer ADV + price; add impact-cost gate if free data allows | Keep V1 simple |

**Challenge:** Delivery % as a hard inclusion filter can churn the universe and bias toward specific styles. Prefer ADV + price floor first; promote delivery to a **feature / risk input**, not membership, unless you insist.

### 5.3 Refresh
- **Weekly** membership recompute (e.g. Friday post-close or Sunday batch using week’s data)  
- Intra-week: apply **exclusions** daily (ban, halt, ASM/GSM) even if liquidity membership is weekly  

### 5.4 Exclusions (hard)
- ASM / GSM  
- F&O ban period  
- Listed &lt; 6 months (IPO/relist policy: 6 calendar months from listing date)  
- Halted securities (on halt day: no rank / no label)  
- Merger / amalgamation windows  
- Major corporate actions windows (definition of “major” → Phase 5; Phase 1 locks that they are excluded)

### 5.5 Point-in-time
All membership and exclusions must be as-of decision date T with no future information (invariant #2).

---

## 6. Success criteria & live path

### 6.1 V1 “good enough to trust”
Qualitative gate (authoritative):

> After **six months of paper trading**, would I be comfortable allocating a **small amount of my own capital**?

Quantitative diagnostics that support that judgment (not substitutes):

- Top-N Longs and Top-N Shorts **risk-adjusted performance after realistic costs** vs equal-weight / random / universe median baselines  
- Rank IC / Spearman vs forward cross-sectional returns (diagnostic)  
- Stability across regimes (no single-regime miracle)  

Hit rate alone is **not** sufficient.

### 6.2 Costs
Evaluation **must** include realistic Indian retail/broker-like round-trip costs (STT, exchange, brokerage, slippage tier). Exact schedule → Phase 9; Phase 1 locks that **zero-cost backtests are not decision-grade**.

### 6.3 Capital path
1. Paper / shadow only until §6.1 gate  
2. Then **very small** live capital  
3. No meaningful capital on day-one live  

---

## 7. Explicit non-goals for Phase 1 / V1 problem statement

- Not forecasting Nifty direction  
- Not blended multi-horizon rank  
- Not calibrated probabilities as a V1 requirement (heuristic OK per charter)  
- Not optimizing a risk-adjusted *training* label in V1 (evaluate risk-adjusted; train cross-sectional outperform prob)  
- Not daily universe churn from liquidity metrics  

---

## 8. Soft Phase 0 preferences (recorded, not locked)

| Item | Preference |
|---|---|
| Language | Python |
| Compute | Local first; cloud later |
| Budget | ≤ ₹2–5k/month if external services needed |
| Data | Official/reliable preferred; **provider abstraction** so sources are swappable (aligns with Phase 2) |

These inform Phase 0 but are finalized only in the Phase 0 ADR.

---

## 9. Open items deferred (intentionally)

| Item | Deferred to |
|---|---|
| Exact ADV/price thresholds if you reject §5.2 defaults | Phase 1 sign-off amendment or Phase 2 |
| Quantile % if not 20/20/60 | Phase 1 sign-off amendment |
| Corporate-action adjustment method | Phase 5 |
| Cost schedule (bps by bucket) | Phase 9 |
| Rank formula `f(...)` and risk penalty | Phase 10 |
| Top-N for paper portfolio (e.g. 10/20) | Phase 9 defaults proposal |
| Provider list | Phase 2 |

---

## 10. Sign-off checklist

Reply with approve / change per line:

```text
§2 Modeling objective (prob. of outperforming + risk-aware rank + risk-adj eval): APPROVE / CHANGE: ...
§3 Definitions (returns, quantiles 20/20/60, three-way probs, outputs): APPROVE / CHANGE: ...
§4 Dual lists (Top Longs + Top Shorts): APPROVE / CHANGE: ...
§5.2 Liquidity defaults (ADV ≥ ₹50cr, price ≥ ₹50; delivery not hard-gate): APPROVE / CHANGE: ...
§5.3–5.4 Weekly refresh + exclusions: APPROVE / CHANGE: ...
§6 Success + costs + 6-month paper path: APPROVE / CHANGE: ...
Phase 1 overall: APPROVE → proceed to Phase 0 questions (then Phase 2) / HOLD
```

After overall APPROVE, this file status becomes **Finalized**, charter §3 Phase 1 is checked, and Phase 0 clarifying questions open next (Python/local/budget already lean-decided).
