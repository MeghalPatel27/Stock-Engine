"""Trading-calendar lookback helper tests."""

from __future__ import annotations

from datetime import date

import pytest

from stock_engine.features.calendar import require_lookback_sessions, sessions_on_or_before

CAL = [
    date(2026, 7, 13),
    date(2026, 7, 14),
    date(2026, 7, 15),
    date(2026, 7, 16),
    date(2026, 7, 17),
]


def test_sessions_on_or_before_window() -> None:
    got = sessions_on_or_before(CAL, date(2026, 7, 16), n=3)
    assert [d.date() for d in got] == [
        date(2026, 7, 14),
        date(2026, 7, 15),
        date(2026, 7, 16),
    ]


def test_require_lookback_ok() -> None:
    got = require_lookback_sessions(CAL, date(2026, 7, 17), 5)
    assert len(got) == 5


def test_require_lookback_insufficient() -> None:
    with pytest.raises(ValueError, match="Insufficient trading sessions"):
        require_lookback_sessions(CAL, date(2026, 7, 14), 5)
