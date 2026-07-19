"""Provider-agnostic data source protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DataArtifact:
    """One staged input file discovered by a DataSource."""

    dataset: str
    path: Path
    provider: str
    session_date: date | None = None


class DataSource(Protocol):
    """Future NSE/broker adapters must satisfy this protocol."""

    provider_id: str

    def list_artifacts(self, as_of_date: date | None = None) -> list[DataArtifact]:
        """Return artifacts available for ingestion."""
        ...
