# ADR-06 Label Pipeline — Review Packet

**Repo:** MeghalPatel27/Stock-Engine  
**Status:** H=5 pipeline implemented + hardened. CI expected green on the hardening PR.  
**Hard rule:** Do not begin model training until this E2E review passes.

## Ask of reviewer

1. Label semantics — Approve / Change  
   (forward return, quantile cuts, `selection_policy`, tie-break, universe modes)
2. Leakage / PIT — Approve / Change  
   (features at T, labels at T+H, training join)
3. Storage / versioning / fail-closed validation — Approve / Change  
   (Parquet layout, embedded quantiles, duplicate-key fail, no silent overwrite)
4. Is H=5 PICK A complete enough to unblock the **Modeling ADR proposal** (docs only)?

## Sign-off amendments already locked

1. Configurable `selection_policy`: `floor` | `ceil` | `nearest` (default `floor`)
2. Universe modes: `pilot` | `l1_intersection` | `phase1_filters`  
   — `pilot` is **not suitable for production benchmarking**
3. Every published row stores `top_quantile` and `bottom_quantile`
4. Publish fails on duplicate `(isin, session_date, horizon, label_version)`

Also present: `sample_weight` (default 1.0), `label_source` (`price_return_v1`), refuse overwrite unless `--overwrite` / version bump.

## Tie-break (locked)

- Bullish top-k: sort `(forward_return desc, isin asc)`, take first `k_top`
- Bearish bottom-k: sort `(forward_return asc, isin asc)`, take first `k_bot`
- On rare overlap after size shrink, bullish wins

## What shipped

| Piece | Path |
|---|---|
| ADR final | `docs/decisions/06-label-generation.md` |
| Compute / validate | `src/stock_engine/labels/compute.py` |
| Quantile policy | `src/stock_engine/labels/quantiles.py` |
| Pipeline + CLI | `src/stock_engine/labels/pipeline.py`, `cli.py` |
| Store | `src/stock_engine/labels/store.py` |
| Config | `config/default.yaml` → `labels.*` |
| Docs | `docs/labels/README.md` |
| Unit + E2E | `tests/unit/labels/` + `tests/fixtures/labels/incoming/` |

## E2E evidence to check

```bash
uv sync --extra dev
uv run pytest tests/unit/labels/ -q
# With published L1 for a real as-of:
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite
```

Dedicated fixtures (`tests/fixtures/labels/incoming/`): 5 ISINs × 6 sessions → non-empty H=5 panel with 1 bullish / 1 bearish / 3 neutral per labeled session under `floor` + 20%/20%.

## Explicit non-goals (still out of scope)

- Horizons other than H=5  
- `phase1_filters` membership/ADV wiring  
- Model training, ranking, purged CV  
- Rewriting published `core/v1` in place (use `core/v2`)

## Suggested verdict format

```text
Overall: APPROVE | APPROVE WITH CHANGES | REJECT
§ Semantics: ...
§ PIT / leakage: ...
§ Storage / validation: ...
Unblock Modeling ADR proposal?: YES | NO (reasons)
```
