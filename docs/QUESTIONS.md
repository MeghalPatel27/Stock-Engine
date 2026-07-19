# Outstanding Questions — Answer Pack

**Status:** Awaiting your answers  
**Date:** 2026-07-19  
**Purpose:** One place for every question still open before we finalize Phase 1 and start Phase 0.

How to use:
1. Fill the **Reply block** at the bottom (copy-paste friendly).
2. For each item: `APPROVE`, a letter choice, a number, or `CHANGE: …` / `DELEGATE`.
3. After this pack is answered → Phase 1 locked → Phase 0 design → then Phase 2.

Full Phase 1 proposal context: [`docs/decisions/01-phase1-proposal.md`](decisions/01-phase1-proposal.md)

---

## Part 1 — Phase 1 sign-off (blocking)

These restate the design proposal. Approve or change.

### Q1. Modeling objective (§2)
Train/rank on **probability of cross-sectional outperformance** (top/bottom quantile).  
Risk + confidence **adjust** rank.  
Success evaluated on **risk-adjusted returns after costs**.

- [ ] APPROVE
- [ ] CHANGE: _______________

### Q2. Core definitions (§3)
- Forward return: **Close(T) → Close(T+N)**
- Labels: **top 20% / bottom 20% / middle 60%** neutral
- Outputs: `p_bullish`, `p_bearish`, `p_neutral` (sum to 1), `risk`, `confidence`, `rank_long`, `rank_short`
- Confidence is **not** a directional probability
- V1 primary horizon: **5 trading days**; 1d and 20d later as **separate** ranks (no blend)

- [ ] APPROVE
- [ ] CHANGE: _______________

### Q3. Product shape (§4)
Always produce **Top Longs** and **Top Shorts** (user may ignore shorts).

- [ ] APPROVE
- [ ] CHANGE: _______________

### Q4. Universe refresh & exclusions (§5.3–5.4)
- Membership refresh: **weekly**
- Daily hard exclusions: ASM/GSM, F&O ban, IPO &lt;6 months, halted, merger windows, major corporate actions

- [ ] APPROVE
- [ ] CHANGE: _______________

### Q5. Success & live path (§6)
- Trust gate: comfortable with **small own capital after 6 months paper trading**
- Evaluation includes **realistic broker costs**
- Path: paper first → then **very small** live capital

- [ ] APPROVE
- [ ] CHANGE: _______________

---

## Part 2 — Phase 1 numbers still open

Proposed defaults — confirm or override.

### Q6. Quantile cutoffs
Proposed: **20% / 20% / 60%** (bullish / bearish / neutral).

- [ ] APPROVE 20/20/60
- [ ] CHANGE to: top ___% / bottom ___% / middle ___%

### Q7. Liquidity filter — ADV
Proposed: **≥ ₹50 crore** average daily traded value (20-session median).

- [ ] APPROVE ₹50 cr
- [ ] CHANGE to: ₹ ___ cr
- [ ] DELEGATE (keep proposal, tune later from data)

### Q8. Liquidity filter — price floor
Proposed: **≥ ₹50**.

- [ ] APPROVE ₹50
- [ ] CHANGE to: ₹ ___
- [ ] DELEGATE

### Q9. Delivery % as membership gate
Proposed: **not a hard inclusion filter** in V1; use as feature / risk input only.

- [ ] APPROVE (not a hard gate)
- [ ] CHANGE: hard-gate at delivery % ≥ ___%
- [ ] DELEGATE

### Q10. Top-N for paper portfolio lists (early default)
How many names on the published Top Longs / Top Shorts lists for paper tracking?

- [ ] Top **10** each
- [ ] Top **20** each
- [ ] Top **___** each
- [ ] DELEGATE (decide in Phase 9)

---

## Part 3 — Phase 0 foundations (answer now so we can move straight after Phase 1)

Soft prefs already noted: Python, local-first, ≤ ₹2–5k/month, provider abstraction. Confirm or refine.

### Q11. Language / runtime
- [ ] APPROVE **Python 3.11+** as sole V1 language
- [ ] CHANGE: _______________

### Q12. Packaging / project layout preference
- [ ] **A)** Simple monorepo: `src/`, `research/`, `tests/`, `docs/` (recommended for 1–2 person team)
- [ ] **B)** Split packages early (`engine-core`, `research`, `serving`)
- [ ] **C)** DELEGATE

### Q13. Environment / reproducibility
- [ ] **A)** `uv` + lockfile (fast, modern) 
- [ ] **B)** `poetry`
- [ ] **C)** plain `venv` + `pip` + `requirements.txt`
- [ ] **D)** DELEGATE

### Q14. Config & secrets
- [ ] **A)** `.env` + gitignored secrets; checked-in example `.env.example`
- [ ] **B)** Other: _______________
- [ ] **C)** DELEGATE

### Q15. Local vs cloud for V1
Confirm:
- [ ] APPROVE **local-first** compute + local disk/parquet; cloud only if forced by data/API needs
- [ ] CHANGE: _______________

### Q16. Monthly budget ceiling (external data/services)
- [ ] APPROVE **₹2–5k/month** hard ceiling for V1
- [ ] CHANGE to: ₹ ___ / month
- [ ] Near-zero only (no paid services in V1)

### Q17. OS / machine assumption
What will the daily batch primarily run on?

- [ ] **A)** Your personal laptop/desktop (specify OS: macOS / Windows / Linux)
- [ ] **B)** Always-on mini PC / home server
- [ ] **C)** Undecided — design for laptop, document later migration
- [ ] **D)** Other: _______________

### Q18. Build-vs-buy posture for V1
- [ ] **A)** Prefer free/open tools; buy only when it clearly saves weeks (recommended)
- [ ] **B)** Willing to pay earlier for reliability within budget
- [ ] **C)** DELEGATE

### Q19. Research vs production separation (invariant #5)
Confirm V1 layout principle:
- [ ] APPROVE separate `research/` (notebooks/experiments) vs `src/` (production pipeline code) from day one
- [ ] CHANGE: _______________

### Q20. Git / quality bar for V1
Minimum bar before merges:
- [ ] **A)** Lint + unit tests on CI (GitHub Actions) even while local-first
- [ ] **B)** Local checks only in V1; CI later
- [ ] **C)** DELEGATE

---

## Part 4 — Light data prefs (feeds Phase 2; not a Phase 2 design yet)

### Q21. Broker / API already available?
List anything you already have (Zerodha, Upstox, Fyers, Angel, etc.), or:

- [ ] None yet
- [ ] Have: _______________

### Q22. Comfort with NSE official free artifacts (bhavcopy, etc.) as primary EOD source?
- [ ] Yes
- [ ] Prefer broker history as primary
- [ ] No preference — propose in Phase 2
- [ ] Notes: _______________

### Q23. Any hard “do not scrape / do not use” constraints?
- [ ] None
- [ ] Yes: _______________

---

## Reply block (copy-paste)

```text
=== Part 1 — Phase 1 sign-off ===
Q1:
Q2:
Q3:
Q4:
Q5:

=== Part 2 — Phase 1 numbers ===
Q6:
Q7:
Q8:
Q9:
Q10:

=== Part 3 — Phase 0 ===
Q11:
Q12:
Q13:
Q14:
Q15:
Q16:
Q17:
Q18:
Q19:
Q20:

=== Part 4 — Data prefs ===
Q21:
Q22:
Q23:

Notes (optional):
```

---

## What happens after you answer

1. Finalize Phase 1 ADR (mark signed-off).  
2. Write Phase 0 design proposal from Part 3 answers → your sign-off.  
3. Only then open Phase 2 (data sourcing) questions/design.
