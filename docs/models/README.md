# Models

Frozen artifacts live under `data/models/{model_name}/{model_version}/` (gitignored).

See [ADR-07](../decisions/07-modeling.md).

## Research train + freeze

```bash
uv run python research/experiments/run_walkforward_train.py --as-of YYYY-MM-DD --overwrite
```

## Score (no labels)

```bash
uv run stock-engine-score --as-of YYYY-MM-DD
```

Ranking: `score = p × confidence × (1 - risk_weight × risk)` with configurable `modeling.risk_weight`.
