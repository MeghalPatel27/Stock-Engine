# Labels

Cross-sectional ternary labels for research / training / evaluation.  
**Never used at inference.** See [ADR-06](../decisions/06-label-generation.md).

## Layout

```text
data/labels/{label_set}/{label_version}/horizon={H}/as_of_date=YYYY-MM-DD/
  labels.parquet
data/metadata/labels/...   # publish manifests
```

## Row schema (self-describing)

| Column | Notes |
|---|---|
| `isin`, `session_date`, `horizon` | Keys (with `label_version`) |
| `forward_return` | `CloseAdj(T+H)/CloseAdj(T)-1` |
| `label` | `bullish` / `bearish` / `neutral` |
| `universe_size` | Names in CS panel that session |
| `top_quantile`, `bottom_quantile` | Embedded cutoffs |
| `selection_policy` | `floor` / `ceil` / `nearest` |
| `universe_mode` | `pilot` / `l1_intersection` / `phase1_filters` |
| `sample_weight` | Default `1.0` |
| `label_source` | Default `price_return_v1` |
| `label_version` | e.g. `v1` |

## Universe modes

| Mode | Use |
|---|---|
| `pilot` | Allow-list / transitional. **Not suitable for production benchmarking.** |
| `l1_intersection` | All L1 names with valid forward return |
| `phase1_filters` | Deferred (F&O membership + ADV/price) |

## PIT

Features use data available at `T`. Labels use outcome at `T+H`.  
Training join is `features(T) ⋈ labels(T)` only when `T+H` is known.

## Publish

```bash
uv run stock-engine-publish-labels --as-of YYYY-MM-DD
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --universe-mode pilot --selection-policy floor
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite   # same version rebuild only
```

V1 supports **horizon=5** only. Never silently rewrite published versions — bump `label_version` (`core/v2`) for semantic changes.
