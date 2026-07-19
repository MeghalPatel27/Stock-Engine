# Stock Intelligence Engine

**Status:** ADR-06 finalized. H=5 **label pipeline** implemented — E2E review next. No model training yet.

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Labels](docs/labels/README.md)
- [Feature backlog](docs/features/FEATURE_BACKLOG.md)
- [Pilot 5 stocks](docs/data/pilot_5_stocks/README.md)
- [ADR-06 review packet](docs/reviews/adr06-label-pipeline-review-packet.md)

## Current gate

Complete [label E2E review](docs/reviews/adr06-label-pipeline-review-packet.md), then **Modeling ADR**.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite
uv run pytest
```
