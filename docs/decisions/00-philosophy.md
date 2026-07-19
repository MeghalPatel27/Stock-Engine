# Decision Record 00 — Architecture Philosophy

**Status:** Finalized  
**Date:** 2026-07-19  
**Phase:** Philosophy (pre-Phase 0)

## Decision

V1 uses a **P3-leaning hybrid architecture** (rules / statistics / ML chosen per component).  
Long-term target is **P2** (modular multi-signal + learned meta-ranking).

V1 is explicitly **"P2 with the learned parts deferred,"** not rules-forever.

## Alternatives considered

| Paradigm | Verdict | Why |
|---|---|---|
| P1 — pure end-to-end ML | Eliminated | Data-hungry, opaque, poor fit for ~180–200 stock universe |
| P2 — modular multi-signal + learned combiner | Deferred (target end-state) | Too much infra before any signal is proven |
| P3 — hybrid per component | Selected for V1 | Fastest path to explainable daily ranking without foreclosing P2 |

## Non-negotiable invariants (locked from day one)

1. Signal contract: `{value, direction, confidence, timestamp, version}`
2. Point-in-time correctness (no lookahead leakage)
3. Pluggable combiner (rule weights ↔ learned stacking behind one interface)
4. Backtest harness measuring per-signal OOS IC / predictive value
5. Research / production code separation

## Intentional V1 debt

Hand-set weights; heuristic (not calibrated) scores; lightweight observability; parquet/tables instead of a feature platform; imperfect human rule priors (mitigated by backtesting every rule before shipping).

## Refused debt

No signal contract, no point-in-time correctness, no research/production separation.

## Migration triggers (V1 → V2)

| Stage | Trigger | Action |
|---|---|---|
| 1 | Signal shows stable OOS IC | Promote signal to ML submodel behind same contract |
| 2 | Multiple proven signals + overlapping history | OOF store + nested WF validation; learned meta-combiner |
| 3 | Signal count grows | Registry, feature store, monitoring, regime gating, multi-horizon multi-task |

## Source of truth

Full charter: [`docs/PROJECT_CHARTER.md`](../PROJECT_CHARTER.md)
