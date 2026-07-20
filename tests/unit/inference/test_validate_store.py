"""Inference validate + store unit tests (no market simulation)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from stock_engine.inference.store import LocalParquetRankStore
from stock_engine.inference.validate import validate_rank_frame


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["AAA", "BBB"],
            "isin": ["INE001", "INE002"],
            "as_of_date": ["2026-07-17", "2026-07-17"],
            "session_date": ["2026-07-17", "2026-07-17"],
            "horizon": [5, 5],
            "p_bullish": [0.7, 0.2],
            "p_bearish": [0.1, 0.6],
            "p_neutral": [None, None],
            "risk": [0.4, 0.5],
            "confidence": [0.6, 0.55],
            "score_long": [0.3, 0.1],
            "score_short": [0.05, 0.25],
            "rank_long": [1, 2],
            "rank_short": [2, 1],
            "model_version": ["v1", "v1"],
            "config_version": ["0.1.0", "0.1.0"],
        }
    )


def test_validate_ok() -> None:
    assert validate_rank_frame(_frame(), horizon=5, model_version="v1") == []


def test_validate_rejects_label_leak() -> None:
    frame = _frame()
    frame["label"] = "bullish"
    errors = validate_rank_frame(frame, horizon=5, model_version="v1")
    assert any("label columns" in e for e in errors)


def test_store_refuse_overwrite(tmp_path: Path) -> None:
    store = LocalParquetRankStore(tmp_path / "ranks")
    kwargs = dict(rank_set="core", rank_version="v1", horizon=5, as_of_date="2026-07-17")
    store.write(_frame(), **kwargs)
    with pytest.raises(FileExistsError, match="overwrite"):
        store.write(_frame(), **kwargs, overwrite=False)
    store.write(_frame(), **kwargs, overwrite=True)
