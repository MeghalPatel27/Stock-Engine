"""Local CSV DataSource — reads user-dropped files from data/incoming/."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from stock_engine.ingest.datasets import DATASETS
from stock_engine.ingest.protocol import DataArtifact

_DATE_SUFFIX = re.compile(
    r"^(?P<dataset>[a-z0-9_]+)__(?P<ymd>\d{4}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE,
)
_PLAIN = re.compile(r"^(?P<dataset>[a-z0-9_]+)\.csv$", re.IGNORECASE)


class LocalIncomingCsvSource:
    """
    Scan `data/incoming/` for known dataset CSVs.

    Accepted names:
      - equity_eod.csv
      - equity_eod__2026-07-18.csv
      - corporate_actions.csv / corporate_actions__YYYY-MM-DD.csv
      - symbol_isin_map.csv / symbol_isin_map__YYYY-MM-DD.csv
    """

    provider_id = "local_csv"

    def __init__(self, incoming_dir: Path) -> None:
        self.incoming_dir = incoming_dir

    def list_artifacts(self, as_of_date: date | None = None) -> list[DataArtifact]:
        if not self.incoming_dir.exists():
            return []

        found: dict[str, DataArtifact] = {}
        for path in sorted(self.incoming_dir.glob("*.csv")):
            parsed = self._parse_name(path.name)
            if parsed is None:
                continue
            dataset, session_date = parsed
            if dataset not in DATASETS:
                continue
            if as_of_date is not None and session_date is not None and session_date != as_of_date:
                continue
            # Prefer dated file for a dataset when multiple exist
            prior = found.get(dataset)
            if prior is None or (session_date is not None and prior.session_date is None):
                found[dataset] = DataArtifact(
                    dataset=dataset,
                    path=path,
                    provider=self.provider_id,
                    session_date=session_date,
                )
        return list(found.values())

    @staticmethod
    def _parse_name(name: str) -> tuple[str, date | None] | None:
        m = _DATE_SUFFIX.match(name)
        if m:
            ymd = datetime.strptime(m.group("ymd"), "%Y-%m-%d").date()
            return m.group("dataset").lower(), ymd
        m = _PLAIN.match(name)
        if m:
            return m.group("dataset").lower(), None
        return None
