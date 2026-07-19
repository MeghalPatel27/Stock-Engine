"""Feature store interfaces and local Parquet implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd


class FeatureStore(Protocol):
    def write(
        self,
        frame: pd.DataFrame,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> Path: ...

    def read(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> pd.DataFrame: ...

    def exists(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> bool: ...


class LocalParquetFeatureStore:
    """
    data/features/{feature_set}/{feature_version}/as_of_date=YYYY-MM-DD/features.parquet
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, feature_set: str, feature_version: str, as_of_date: str) -> Path:
        return (
            self.root
            / feature_set
            / feature_version
            / f"as_of_date={as_of_date}"
            / "features.parquet"
        )

    def write(
        self,
        frame: pd.DataFrame,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> Path:
        required = {"isin", "session_date"}
        missing = required - set(frame.columns)
        if missing:
            msg = f"Feature frame missing columns: {sorted(missing)}"
            raise ValueError(msg)

        out = frame.copy()
        # Deterministic order
        sort_cols = [c for c in ("isin", "session_date") if c in out.columns]
        out = out.sort_values(sort_cols).reset_index(drop=True)

        path = self._path(feature_set, feature_version, as_of_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)
        return path

    def read(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> pd.DataFrame:
        path = self._path(feature_set, feature_version, as_of_date)
        if not path.exists():
            msg = f"Feature set not found: {path}"
            raise FileNotFoundError(msg)
        return pd.read_parquet(path)

    def exists(
        self,
        *,
        feature_set: str,
        feature_version: str,
        as_of_date: str,
    ) -> bool:
        return self._path(feature_set, feature_version, as_of_date).exists()
