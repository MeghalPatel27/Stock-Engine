# Features

**Backlog (done + planned):** [FEATURE_BACKLOG.md](FEATURE_BACKLOG.md)

## Layout

```text
docs/features/
  families.yaml              # feature families
  datasets.yaml              # feature-input datasets (dataset:<id>)
  registry/                  # one YAML per feature
  FEATURE_BACKLOG.md
  README.md
data/features/               # published Parquet (gitignored contents)
```

## Lint

```bash
uv run stock-engine-lint-features
```

CI runs this on every PR.

## Registered features (V1 planned set)

25 features across raw, momentum, trend, volatility, liquidity, cross-sectional.  
See [FEATURE_BACKLOG.md](FEATURE_BACKLOG.md) for the full table.

```bash
# Requires published L1 (+ calendar) for the same as-of partition
uv run stock-engine-publish-features --as-of YYYY-MM-DD
```
