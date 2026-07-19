# Phase 1 — Clarifying Questions (Problem Formulation)

**Status:** Answered — see [01-phase1-proposal.md](01-phase1-proposal.md) for design proposal (awaiting sign-off)  
**Date opened:** 2026-07-19  
**Date answered:** 2026-07-19

Answers are locked into the proposal document. This file remains as the question archive.

---

## Recorded answers

### A. Target & benchmark
- **A1:** C — outperform F&O universe cross-section (not Nifty 50). Ranking engine, not index forecasting.
- **A2:** B (+ dual lists) — ranking primary; probs/confidence/risk supporting; portfolio from rank; always Top Longs + Top Shorts.
- **A3:** A — Close(T) → Close(T+N).

### B. Scores
- **B1:** C — top/bottom quantiles (default 20%/20%, middle neutral).
- **B2:** D/composite — downside vol + drawdown + prediction uncertainty + liquidity + event exposure (never vol-only).
- **B3:** D/composite — model agreement + signal agreement + regime familiarity + data quality (not prediction probability).
- **B4:** B — allow neutral mass; bullish + bearish + neutral = 1.

### C. Horizons
- **C1:** A — 5-day first.
- **C2:** A — separate ranks per horizon; no blending in V1.

### D. Universe
- **D1:** C — F&O + liquidity filters (ADV, turnover, delivery %, price floor — exact gates proposed in design doc).
- **D2:** B — weekly refresh.
- **D3:** ASM/GSM, F&O ban, IPO &lt;6 months, halted, merger periods, major corporate actions.
- **D4:** C — both long and short.

### E. Success
- **E1:** Own-capital comfort after six months successful paper trading; risk-adjusted returns after realistic costs (not hit rate / IC alone).
- **E2:** C — realistic broker costs in evaluation.
- **E3:** A then B — six months paper, then very small live capital.

### F. Soft Phase 0 prefs
- **F1:** Python.
- **F2:** Local first, cloud later.
- **F3:** ≤ ₹2–5k/month if external services needed.
- **F4:** Prefer official/reliable sources; abstraction layer for provider swap.

### Additional gap (raised by user)
- Optimize for expected return vs risk-adjusted return vs probability of outperforming → resolved in proposal §2 (recommended: cross-sectional probability of outperforming for training/rank target; risk-adjusted after-cost evaluation).
