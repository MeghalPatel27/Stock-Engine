# Outstanding Questions — Answer Pack

**Status:** Answered 2026-07-19  
**Superseded for open work by:** Phase 0 sign-off checklist in [`docs/decisions/02-phase0-proposal.md`](decisions/02-phase0-proposal.md)

This file is the archive of the consolidated Q1–Q23 pack and the recorded answers.

---

## Recorded answers (summary)

### Part 1 — Phase 1 sign-off
| Q | Result |
|---|---|
| Q1 | APPROVE — cross-sectional outperform probability; rank primary; risk/confidence modify; risk-adj after costs |
| Q2 | CHANGE — outputs required; **do not** enforce `p_bull+p_bear+p_neutral=1` as invariant; `p_neutral` optional |
| Q3 | APPROVE — Top Longs + Top Shorts |
| Q4 | APPROVE — weekly refresh; daily exclusions list |
| Q5 | APPROVE — 6 months paper trust gate; realistic costs; tiny live later |

### Part 2 — Numbers
| Q | Result |
|---|---|
| Q6 | APPROVE 20/20/60 |
| Q7 | CHANGE — `adv_min` default ₹50 Cr, **configurable** |
| Q8 | APPROVE ₹50 price min, configurable |
| Q9 | APPROVE delivery % not membership filter |
| Q10 | APPROVE Top 20 Longs / Top 20 Shorts |

### Part 3 — Phase 0
| Q | Result |
|---|---|
| Q11–Q20 | All APPROVE as proposed (Python 3.11+, monorepo, uv, .env, local-first, ₹2–5k, laptop, OSS-first, research/src split, Ruff+tests+GHA CI) |

### Part 4 — Data prefs
| Q | Result |
|---|---|
| Q21 | None yet |
| Q22 | No preference — evaluate in Phase 2 |
| Q23 | None |

### Additional notes applied
1. Every finalized decision → ADR  
2. No hardcoded thresholds — configuration  
3. Engine contracts independent of model implementation  
4. Next deliverable after Phase 1 lock = **Phase 0 Architecture Proposal** (done: `02-phase0-proposal.md`), not implementation / not Phase 2 yet  

---

## What is open now

Sign off Phase 0 using the checklist at the end of [`docs/decisions/02-phase0-proposal.md`](decisions/02-phase0-proposal.md).
