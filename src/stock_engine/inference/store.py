"""Local Parquet rank store."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class LocalParquetRankStore:
    """
    data/ranks/{rank_set}/{rank_version}/horizon={H}/as_of_date=YYYY-MM-DD/ranks.parquet
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, rank_set: str, rank_version: str, horizon: int, as_of_date: str) -> Path:
        return (
            self.root
            / rank_set
            / rank_version
            / f"horizon={horizon}"
            / f"as_of_date={as_of_date}"
            / "ranks.parquet"
        )

    def write(
        self,
        frame: pd.DataFrame,
        *,
        rank_set: str,
        rank_version: str,
        horizon: int,
        as_of_date: str,
        overwrite: bool = False,
    ) -> Path:
        path = self._path(rank_set, rank_version, horizon, as_of_date)
        if path.exists() and not overwrite:
            msg = (
                f"Refusing to overwrite existing ranks at {path}. "
                "Bump rank_version or pass overwrite=True."
            )
            raise FileExistsError(msg)
        out = frame.sort_values(["rank_long", "symbol"]).reset_index(drop=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(path, index=False)
        return path

    def read(
        self,
        *,
        rank_set: str,
        rank_version: str,
        horizon: int,
        as_of_date: str,
    ) -> pd.DataFrame:
        path = self._path(rank_set, rank_version, horizon, as_of_date)
        if not path.exists():
            msg = f"Rank set not found: {path}"
            raise FileNotFoundError(msg)
        return pd.read_parquet(path)

    def exists(
        self,
        *,
        rank_set: str,
        rank_version: str,
        horizon: int,
        as_of_date: str,
    ) -> bool:
        return self._path(rank_set, rank_version, horizon, as_of_date).exists()
