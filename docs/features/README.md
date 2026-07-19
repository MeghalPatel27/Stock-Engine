# Features

## Layout

```text
docs/features/
  families.yaml              # feature families
  registry/                  # one YAML per feature (empty until Feature Implementation)
  README.md
data/features/               # published Parquet (gitignored contents)
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
