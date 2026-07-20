"""Integration: infer publish on real pilot features + frozen model."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from stock_engine.inference.pipeline import run_inference_publish
from stock_engine.inference.store import LocalParquetRankStore

DATA = Path(__file__).resolve().parents[2] / "data"
AS_OF = date(2026, 7, 17)


def _ready() -> bool:
    return (
        (DATA / "features" / "core" / "v1" / f"as_of_date={AS_OF}" / "features.parquet").exists()
        and (DATA / "models" / "cs_quantile_h5" / "v1" / "train_manifest.json").exists()
        and (DATA / "clean" / "l1" / "equity_eod" / f"as_of_date={AS_OF}").exists()
    )


@pytest.mark.skipif(not _ready(), reason="published pilot features/model not present")
def test_infer_publish_real_pilot() -> None:
    result = run_inference_publish(
        data_root=DATA,
        as_of_date=AS_OF,
        rank_set="core",
        rank_version="v1",
        overwrite=True,
    )
    assert result.status == "success", result.errors
    assert result.manifest is not None
    assert result.manifest.row_count == 5
    assert len(result.top_longs) == 5
    assert len(result.top_shorts) == 5

    store = LocalParquetRankStore(DATA / "ranks")
    got = store.read(rank_set="core", rank_version="v1", horizon=5, as_of_date=AS_OF.isoformat())
    assert set(got["symbol"]) == {"RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"}
    assert "label" not in got.columns
    assert "forward_return" not in got.columns

    # Refuse overwrite
    again = run_inference_publish(
        data_root=DATA,
        as_of_date=AS_OF,
        overwrite=False,
    )
    assert again.status == "failed"
    assert any("overwrite" in e.lower() or "Refusing" in e for e in again.errors)
