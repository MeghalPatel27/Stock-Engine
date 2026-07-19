"""Load published feature/label partitions for modeling."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.store import LocalParquetFeatureStore
from stock_engine.labels.store import LocalParquetLabelStore
from stock_engine.models.join import build_train_matrix


def load_feature_frame(
    data_root: Path,
    *,
    feature_set: str,
    feature_version: str,
    as_of_date: date | str,
) -> pd.DataFrame:
    store = LocalParquetFeatureStore(data_root / "features")
    return store.read(
        feature_set=feature_set,
        feature_version=feature_version,
        as_of_date=str(as_of_date),
    )


def load_label_frame(
    data_root: Path,
    *,
    label_set: str,
    label_version: str,
    horizon: int,
    as_of_date: date | str,
) -> pd.DataFrame:
    store = LocalParquetLabelStore(data_root / "labels")
    return store.read(
        label_set=label_set,
        label_version=label_version,
        horizon=horizon,
        as_of_date=str(as_of_date),
    )


def load_train_matrix(
    data_root: Path,
    *,
    as_of_date: date | str,
    feature_columns: list[str] | None = None,
    feature_set: str = "core",
    feature_version: str = "v1",
    label_set: str = "core",
    label_version: str = "v1",
    horizon: int = 5,
) -> pd.DataFrame:
    features = load_feature_frame(
        data_root,
        feature_set=feature_set,
        feature_version=feature_version,
        as_of_date=as_of_date,
    )
    labels = load_label_frame(
        data_root,
        label_set=label_set,
        label_version=label_version,
        horizon=horizon,
        as_of_date=as_of_date,
    )
    return build_train_matrix(
        features,
        labels,
        feature_columns=feature_columns,
        horizon=horizon,
    )


def load_symbol_map_from_l1(data_root: Path, as_of_date: date | str) -> dict[str, str]:
    """Map isin → symbol from published L1 equity (best-effort)."""
    path = (
        data_root
        / "clean"
        / "l1"
        / "equity_eod"
        / f"as_of_date={as_of_date}"
        / "equity_eod__v1.parquet"
    )
    if not path.exists():
        # try glob
        parent = data_root / "clean" / "l1" / "equity_eod" / f"as_of_date={as_of_date}"
        if parent.exists():
            cands = list(parent.glob("*.parquet"))
            if cands:
                path = cands[0]
            else:
                return {}
        else:
            return {}
    eq = pd.read_parquet(path, columns=["isin", "symbol"])
    eq = eq.dropna(subset=["isin", "symbol"]).drop_duplicates("isin")
    return dict(zip(eq["isin"].astype(str), eq["symbol"].astype(str), strict=False))
