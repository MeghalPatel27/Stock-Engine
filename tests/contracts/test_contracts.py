"""Contract tests — schemas accept valid rows; no simplex sum required."""

from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from stock_engine.contracts import RankRow, RunMetadata, Signal


def test_signal_ok() -> None:
    s = Signal(
        value=0.5,
        direction="bullish",
        confidence=0.8,
        timestamp=datetime.now(UTC),
        version="0.1.0",
    )
    assert s.direction == "bullish"


def test_rank_row_without_neutral_and_without_sum_to_one() -> None:
    row = RankRow(
        symbol="RELIANCE",
        as_of_date=date(2026, 7, 18),
        horizon=5,
        p_bullish=0.7,
        p_bearish=0.6,  # deliberately does not form a simplex with bullish
        risk=0.3,
        confidence=0.5,
        rank_long=1,
        rank_short=50,
        model_version="m0",
        config_version="0.1.0",
    )
    assert row.p_neutral is None
    assert row.p_bullish + row.p_bearish != pytest.approx(1.0)


def test_rank_row_optional_neutral() -> None:
    row = RankRow(
        symbol="TCS",
        as_of_date=date(2026, 7, 18),
        horizon=5,
        p_bullish=0.4,
        p_bearish=0.2,
        p_neutral=0.4,
        risk=0.2,
        confidence=0.7,
        rank_long=3,
        rank_short=40,
        model_version="m0",
        config_version="0.1.0",
    )
    assert row.p_neutral == 0.4


def test_run_metadata_ok() -> None:
    meta = RunMetadata(
        run_id="abc",
        as_of_date=date(2026, 7, 18),
        config_hash="deadbeef",
        config_version="0.1.0",
        engine_version="0.1.0",
        timestamp=datetime.now(UTC),
    )
    assert meta.run_id == "abc"


def test_rank_row_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        RankRow(
            symbol="X",
            as_of_date=date(2026, 7, 18),
            horizon=5,
            p_bullish=1.5,
            p_bearish=0.1,
            risk=0.1,
            confidence=0.1,
            rank_long=1,
            rank_short=1,
            model_version="m0",
            config_version="0.1.0",
        )
