# Stock Intelligence Engine

**Status:** Cleaning approved. Next: sign off **Feature Registry** design (ADR-05). No features yet.

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Incoming CSV](docs/data/incoming.md)
- [Data dictionary](docs/data/dictionary/)
- [Data requirements vs public availability](docs/data/DATA_AVAILABILITY.md)
- [Pilot 5 stocks — CSV templates & sources](docs/data/pilot_5_stocks/README.md)

## Current gate

[`docs/decisions/05-phase-feature-registry-proposal.md`](docs/decisions/05-phase-feature-registry-proposal.md)

## Quickstart (data)

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run pytest
```
