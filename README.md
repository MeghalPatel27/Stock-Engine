# Stock Intelligence Engine

**Status:** H=5 labels E2E **APPROVED**. [Modeling ADR proposal](docs/decisions/07-phase-modeling-proposal.md) next (docs only — no training yet).

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Labels](docs/labels/README.md)
- [Feature backlog](docs/features/FEATURE_BACKLOG.md)
- [Pilot 5 stocks](docs/data/pilot_5_stocks/README.md)
- [Modeling ADR proposal](docs/decisions/07-phase-modeling-proposal.md)

## Current gate

Review and sign off the **Modeling ADR**. Do not implement training until it is Finalized.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-publish-labels --as-of YYYY-MM-DD --overwrite
uv run pytest
```
