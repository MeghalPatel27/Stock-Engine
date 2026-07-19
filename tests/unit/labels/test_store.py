"""Label store + content-hash tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from stock_engine.labels.hashing import label_content_hash
from stock_engine.labels.store import LocalParquetLabelStore


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "isin": ["INE002", "INE001"],
            "session_date": [pd.Timestamp("2026-07-10"), pd.Timestamp("2026-07-10")],
            "horizon": [5, 5],
            "forward_return": [0.1, -0.1],
            "label": ["bullish", "bearish"],
            "universe_size": [2, 2],
            "label_version": ["v1", "v1"],
            "universe_mode": ["pilot", "pilot"],
            "selection_policy": ["floor", "floor"],
            "top_quantile": [0.2, 0.2],
            "bottom_quantile": [0.2, 0.2],
            "sample_weight": [1.0, 1.0],
            "label_source": ["price_return_v1", "price_return_v1"],
        }
    )


def test_roundtrip_and_sort(tmp_path: Path) -> None:
    store = LocalParquetLabelStore(tmp_path / "labels")
    path = store.write(
        _frame(),
        label_set="core",
        label_version="v1",
        horizon=5,
        as_of_date="2026-07-18",
    )
    assert path.exists()
    got = store.read(
        label_set="core",
        label_version="v1",
        horizon=5,
        as_of_date="2026-07-18",
    )
    assert list(got["isin"]) == ["INE001", "INE002"]


def test_refuse_overwrite(tmp_path: Path) -> None:
    store = LocalParquetLabelStore(tmp_path / "labels")
    kwargs = dict(
        label_set="core",
        label_version="v1",
        horizon=5,
        as_of_date="2026-07-18",
    )
    store.write(_frame(), **kwargs)
    with pytest.raises(FileExistsError, match="overwrite"):
        store.write(_frame(), **kwargs, overwrite=False)
    store.write(_frame(), **kwargs, overwrite=True)


def test_content_hash_stable_under_column_reorder() -> None:
    a = _frame()
    b = a[
        [
            "label_source",
            "isin",
            "session_date",
            "horizon",
            "forward_return",
            "label",
            "universe_size",
            "label_version",
            "universe_mode",
            "selection_policy",
            "top_quantile",
            "bottom_quantile",
            "sample_weight",
        ]
    ].copy()
    assert label_content_hash(a) == label_content_hash(b)
