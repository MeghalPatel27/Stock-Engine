"""Integration: backtest must use published real pilot partitions (skip if absent)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from stock_engine.backtest.costs import DeliveryCostModel
from stock_engine.backtest.engine import run_walkforward_backtest

DATA = Path(__file__).resolve().parents[2] / "data"
AS_OF = date(2026, 7, 17)


def _real_partitions_present() -> bool:
    return (
        (DATA / "clean" / "l1" / "equity_eod" / f"as_of_date={AS_OF}").exists()
        and (
            DATA / "features" / "core" / "v1" / f"as_of_date={AS_OF}" / "features.parquet"
        ).exists()
        and (
            DATA / "labels" / "core" / "v1" / "horizon=5" / f"as_of_date={AS_OF}" / "labels.parquet"
        ).exists()
    )


@pytest.mark.skipif(not _real_partitions_present(), reason="published pilot data not present")
def test_backtest_on_real_pilot_data() -> None:
    result = run_walkforward_backtest(
        data_root=DATA,
        as_of_date=AS_OF,
        horizon=5,
        top_k=1,  # pilot has 5 names
        risk_weight=1.0,
        capital_inr=1_000_000.0,
        cost_model=DeliveryCostModel.from_config(None),
        modeling_cfg={
            "embargo_sessions": 5,
            "min_train_sessions": 252,
            "test_fold_sessions": 21,
            "step_sessions": 21,
            "random_seed": 42,
            "max_iter": 80,
            "max_depth": 4,
            "min_samples_leaf": 20,
            "learning_rate": 0.05,
            "l2_regularization": 1.0,
            "max_leaf_nodes": 31,
        },
    )
    assert result.status == "success", result.errors
    assert result.metrics["history_sessions"] >= 1000
    assert result.metrics["universe_n_isins"] == 5
    assert result.metrics["n_periods"] > 0
    assert result.trades is not None and len(result.trades) > 0
    # Trades must be real pilot ISINs only
    allowed = {
        "INE002A01018",
        "INE467B01029",
        "INE009A01021",
        "INE040A01034",
        "INE090A01021",
    }
    assert set(result.trades["isin"]).issubset(allowed)
