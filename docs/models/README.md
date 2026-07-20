# Models

Frozen artifacts under `data/models/{model_name}/{model_version}/`.

## Training modes

| Mode | Config | Use case |
|---|---|---|
| `pooled` | `model_name: cs_quantile_h5` | Cross-sectional single model |
| **`per_stock`** | `model_name: cs_quantile_h5_per_stock` | **Pilot default** — one tuned model per ISIN |

## Per-stock train (pilot)

Uses only published real features + labels for each ISIN (~1200+ sessions each):

```bash
uv run python research/experiments/run_per_stock_train.py --as-of 2026-07-17 --overwrite
```

Layout:

```text
data/models/cs_quantile_h5_per_stock/v1/
  bundle_manifest.json
  metrics_per_stock.json
  by_isin/INE002A01018/...
```

## Score / infer

```bash
uv run stock-engine-infer --as-of 2026-07-17 --overwrite
```

Scorer loads the matching ISIN model for each name automatically.

See [ADR-07](../decisions/07-modeling.md).
