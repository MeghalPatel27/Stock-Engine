"""Local Parquet label store."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class LocalParquetLabelStore:
    """
    data/labels/{label_set}/{label_version}/horizon={H}/as_of_date=YYYY-MM-DD/labels.parquet
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, label_set: str, label_version: str, horizon: int, as_of_date: str) -> Path:
        return (
            self.root
            / label_set
            / label_version
            / f"horizon={horizon}"
            / f"as_of_date={as_of_date}"
            / "labels.parquet"
        )

    def write(
        self,
        frame: pd.DataFrame,
        *,
        label_set: str,
        label_version: str,
        horizon: int,
        as_of_date: str,
        overwrite: bool = False,
    ) -> Path:
        path = self._path(label_set, label_version, horizon, as_of_date)
        if path.exists() and not overwrite:
            msg = (
                f"Refusing to overwrite existing labels at {path}. "
                "Bump label_version or pass overwrite=True for intentional rebuild."
            )
            raise FileExistsError(msg)

        out = frame.sort_values(["isin", "session_date"]).reset_index(drop=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)
        return path

    def read(
        self,
        *,
        label_set: str,
        label_version: str,
        horizon: int,
        as_of_date: str,
    ) -> pd.DataFrame:
        path = self._path(label_set, label_version, horizon, as_of_date)
        if not path.exists():
            msg = f"Label set not found: {path}"
            raise FileNotFoundError(msg)
        return pd.read_parquet(path)

    def exists(
        self,
        *,
        label_set: str,
        label_version: str,
        horizon: int,
        as_of_date: str,
    ) -> bool:
        return self._path(label_set, label_version, horizon, as_of_date).exists()
