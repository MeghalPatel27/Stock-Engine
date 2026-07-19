# Features

## Layout

```text
docs/features/
  families.yaml              # feature families
  datasets.yaml              # feature-input datasets (dataset:<id>)
  registry/                  # one YAML per feature (empty until Feature Implementation)
  README.md
data/features/               # published Parquet (gitignored contents)
```

## Lint

```bash
uv run stock-engine-lint-features
```

CI runs this on every PR.

## Registered features

| Feature id | Type | Notes |
|---|---|---|
| `raw__close_adj__l1@v1` | raw | L1 `close_adj` projection |
| `mom__ret__1d@v1` | rolling | 1-session simple return; depends on raw close |
| `mom__ret__5d@v1` | rolling | 5-session simple return; depends on raw close |
| `mom__ret__20d@v1` | rolling | 20-session simple return; depends on raw close |

```bash
# Requires published L1 (+ calendar) for the same as-of partition
uv run stock-engine-publish-features --as-of YYYY-MM-DD
# or only momentum (auto-includes upstream raw):
uv run stock-engine-publish-features --as-of YYYY-MM-DD --feature-id mom__ret__1d@v1
```

## Rules (ADR-05)

- Register features before implementing compute.  
- Combiner consumes **signals**, not raw features.  
- Framework first; concrete features only after framework review.  
- Lookbacks use the canonical trading calendar.  
- Production lifecycle = fail-closed validation.  
- Every feature declares `feature_type` and a `family`.  

## Feature YAML schema

See `stock_engine.features.models.FeatureSpec` and fixtures under `tests/fixtures/features/`.

Required fields include: `name`, `version`, `family`, `feature_type`, `owner`, `description`,
`dtype`, `dependencies`, `lookback_sessions`, `pit_rule`, `null_policy`, `lifecycle`,
`validation`, `recomputable`.

Optional: `unit`, `computational_cost`, `stability`.
