# Inference

Daily post-close rank publish from **frozen** models. Labels are never read.

See [ADR-09](../decisions/09-inference-serving.md).

## Layout

```text
data/ranks/{rank_set}/{rank_version}/horizon=H/as_of_date=YYYY-MM-DD/
  ranks.parquet
  signals.json
data/metadata/ranks/published/{as_of}/...
```

## Run

Requires published features + frozen model for the same as-of:

```bash
uv run stock-engine-infer --as-of 2026-07-17 --overwrite
```

Outputs Top Longs / Top Shorts on stdout (capped by `output.top_n_*`).
