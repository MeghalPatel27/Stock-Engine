# Stock Intelligence Engine

**Status:** 25 features on `main`. Next: sign off **Label Generation** (ADR-06).

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Feature backlog](docs/features/FEATURE_BACKLOG.md)
- [Incoming CSV](docs/data/incoming.md)
- [Data dictionary](docs/data/dictionary/)
- [Pilot 5 stocks](docs/data/pilot_5_stocks/README.md)

## Current gate

[`docs/decisions/06-phase-label-generation-proposal.md`](docs/decisions/06-phase-label-generation-proposal.md)

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-lint-features
uv run pytest
```
