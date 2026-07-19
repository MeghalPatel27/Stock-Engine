# Phase 1 — Clarifying Questions (Problem Formulation)

**Status:** Awaiting answers  
**Date opened:** 2026-07-19  
**Rule:** No Phase 1 design proposal until these are answered. No Phase 0 tech lock until Phase 1 is finalized (language/runtime may be discussed in parallel).

Answer with letters (A/B/C…) and short notes where a free-text line is shown. If unsure, pick the closest option and say what feels wrong about it.

---

## A. Target & benchmark (what “outperform” means)

### A1. Primary target for ranking
Which return definition should drive the daily rank?

- **A)** Relative to Nifty 50 (stock return − index return over the horizon)
- **B)** Relative to sector / industry peer average
- **C)** Relative to the cross-section of our own F&O universe (rank/percentile of return within universe)
- **D)** Absolute return (no benchmark subtraction)
- **E)** Other: _______________

### A2. Directional outputs vs ranking objective
Bullish/bearish probabilities and the rank list should optimize for:

- **A)** Same thing — probabilities are the primary target; rank is just a sort of a single score derived from them
- **B)** Rank is primary (cross-sectional opportunity list); probabilities are secondary / interpretive
- **C)** Separate: long-side opportunity rank and short-side opportunity rank (two lists)
- **D)** Other: _______________

### A3. Holding / evaluation convention for labels
When we say “5 trading days,” how do we measure the outcome from the decision time (after T close)?

- **A)** Close(T) → close(T+H)  *(standard; assumes decision usable for next open or T+1 close)*
- **B)** Open(T+1) → close(T+H)  *(more realistic if you act next morning)*
- **C)** Open(T+1) → open(T+1+H)
- **D)** Undecided — recommend after tradeoffs

---

## B. Label construction & score semantics

### B1. Bullish / bearish labels (for training & evaluation)
How should the binary (or ternary) label be defined?

- **A)** Sign of excess return vs benchmark (bullish if excess > 0)
- **B)** Thresholded: bullish if excess > +X%, bearish if excess < −X%, else neutral (you set X or we propose)
- **C)** Top/bottom quantile within the day’s universe (e.g. top 20% bullish, bottom 20% bearish)
- **D)** Other: _______________

If B: preferred X% per horizon (1d / 5d / 20d), or “propose defaults.”

### B2. Meaning of **risk score** (0–1 or similar)
What should a high risk score mean?

- **A)** Expected downside / drawdown severity if the trade goes wrong (volatility / left-tail)
- **B)** Uncertainty / instability of the prediction itself (model disagreement, low confidence)
- **C)** Event / idiosyncratic risk (earnings, corporate action, halt, rollover week)
- **D)** Composite of A + C (prediction uncertainty stays in confidence)
- **E)** Other: _______________

### B3. Meaning of **confidence score**
What should a high confidence score mean?

- **A)** Strength of agreement across signals (and later, model calibration)
- **B)** Data quality / completeness for that name that day
- **C)** Historical reliability of this signal mix in the current regime
- **D)** Composite of A + B (regime reliability deferred)
- **E)** Other: _______________

### B4. Must bullish_prob + bearish_prob = 1?
- **A)** Yes (binary; neutral absorbed into both or neither)
- **B)** No — allow a neutral mass: bullish + bearish + neutral = 1
- **C)** Undecided — recommend after tradeoffs

---

## C. Horizons for V1

### C1. Horizon priority
- **A)** Ship **5d first**; add 1d and 20d after the pipeline works
- **B)** Ship **1d first** (fastest feedback loop)
- **C)** Ship **20d first** (more signal, less noise)
- **D)** All three in V1 from day one
- **E)** Other: _______________

### C2. Multi-horizon reconciliation in V1
If more than one horizon ships:
- **A)** Separate ranks per horizon (three lists)
- **B)** One blended “opportunity” rank with explicit horizon weights
- **C)** Primary horizon rank only; others shown as secondary columns
- **D)** Defer until we know which horizon is primary

---

## D. Universe rules

### D1. Exact universe definition (starting point)
- **A)** All current NSE F&O equity underlying stocks (~180–200), no further filter
- **B)** F&O equities ∩ Nifty 100 (or Nifty 50) — tighter large-cap only
- **C)** F&O equities with liquidity floors (ADV, impact cost, bid-ask) — propose thresholds
- **D)** Hand-curated static list you maintain — paste or attach list
- **E)** Other: _______________

### D2. Universe reselection frequency
- **A)** Daily (membership as of that day’s official F&O list / criteria)
- **B)** Weekly
- **C)** Monthly / on F&O contract cycle
- **D)** Quarterly
- **E)** Undecided — recommend after tradeoffs

### D3. Hard exclusions (check all that apply)
- [ ] Stocks in ban period / F&O ban
- [ ] Recent listing / IPO within N months (N = ___ )
- [ ] Corporate action window (bonus/split/merger) around event
- [ ] Halted / circuit-hit days for labeling and/or ranking
- [ ] Low free-float / known manipulation watchlist (define source)
- [ ] Other: _______________

### D4. Long-only vs long/short use case
How will you primarily use the daily list?

- **A)** Long-only stock picks (cash / delivery / positional)
- **B)** Long/short relative value within the universe
- **C)** Both — design must support both
- **D)** Undecided for V1; optimize for long-only first

---

## E. Success bar for V1

### E1. What makes V1 “good enough to trust”?
Pick the closest, and optionally rewrite in your own words.

- **A)** Top-decile (or top-N) picks beat the benchmark on average after costs over a walk-forward period
- **B)** Rank IC / Spearman correlation vs forward excess returns is stably positive OOS
- **C)** Hit rate on direction above a floor (e.g. >55% on 5d) with controlled drawdowns
- **D)** Qualitative: “I would size a small real capital sleeve on the top ranks”
- **E)** Other / your words: _______________

### E2. Cost assumptions for “after costs” success (if relevant)
- **A)** Ignore costs in V1 metrics; add later
- **B)** Simple round-trip cost assumption (e.g. X bps) — you set X or we propose
- **C)** Broker-realistic (STT, exchange, slippage tier by ADV) from the start

### E3. Paper vs real capital intent for first live season
- **A)** Paper / shadow rankings only until backtest bar is met
- **B)** Tiny live sleeve in parallel with paper
- **C)** Undecided

---

## F. Parallel Phase 0 soft preferences (non-binding until Phase 0)

Answer only if you already have a preference; otherwise mark **delegate**.

### F1. Language / runtime
- **A)** Python-first (recommended default for this problem)
- **B)** Hard constraint: _______________
- **C)** Delegate

### F2. Where should V1 compute/storage live?
- **A)** Local machine primarily
- **B)** Cheap cloud (single VPS / object storage)
- **C)** Hybrid: local research, cloud batch later
- **D)** Delegate given “low budget”

### F3. Monthly infra budget ceiling (USD or INR)
- **A)** Near-zero (free tier / local only)
- **B)** Up to ___ / month
- **C)** Delegate a recommendation with options

### F4. Data sources already in hand or preferred
List anything you already have or prefer (NSE bhavcopy, broker API name, paid vendor, Yahoo/NSE scrape stance, etc.). If none: **none yet — propose free-first stack in Phase 2**.

---

## Response format (copy-paste)

```text
A1:
A2:
A3:
B1:
B2:
B3:
B4:
C1:
C2:
D1:
D2:
D3:
D4:
E1:
E2:
E3:
F1:
F2:
F3:
F4:
Notes (optional):
```

After answers land, the next deliverable is a **Phase 1 design proposal** (target definition, label specs, score semantics, universe rules, success metrics) for explicit sign-off — still no code, still no Phase 0 tech lock.
