# Stock Intelligence Engine

**Status:** V1 planned features implemented (25). Next: Label Generation ADR.

## Docs

- [Charter](docs/PROJECT_CHARTER.md)
- [ADRs](docs/decisions/)
- [Feature registry notes](docs/features/)
- [Incoming CSV](docs/data/incoming.md)
- [Data dictionary](docs/data/dictionary/)
- [Data requirements vs public availability](docs/data/DATA_AVAILABILITY.md)
- [Pilot 5 stocks — CSV templates & sources](docs/data/pilot_5_stocks/README.md)

## Current gate

Review feature set, then **Label Generation ADR**.

## Quickstart

```bash
uv sync --extra dev
uv run stock-engine-ingest --as-of YYYY-MM-DD
uv run stock-engine-publish-features --as-of YYYY-MM-DD
uv run stock-engine-lint-features
uv run pytest
```
