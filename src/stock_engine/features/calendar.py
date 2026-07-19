"""Trading-calendar lookback helpers (no feature formulas)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

import pandas as pd


def _to_timestamp(value: date | datetime | pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts.normalize()


CalendarLike = Sequence[date | datetime | pd.Timestamp] | pd.DatetimeIndex


def open_sessions(calendar: CalendarLike) -> pd.DatetimeIndex:
    """Normalize a calendar to ascending unique session timestamps."""
    idx = pd.DatetimeIndex(pd.to_datetime(list(calendar))).normalize().unique().sort_values()
    return idx


def sessions_on_or_before(
    calendar: CalendarLike,
    as_of: date | datetime | pd.Timestamp,
    *,
    n: int | None = None,
) -> pd.DatetimeIndex:
    """
    Return open sessions with session_date <= as_of (ascending).

    If ``n`` is set, return at most the last ``n`` such sessions (still ascending).
    """
    if n is not None and n < 0:
        msg = "n must be >= 0"
        raise ValueError(msg)

    sessions = open_sessions(calendar)
    cutoff = _to_timestamp(as_of)
    eligible = sessions[sessions <= cutoff]
    if n is None:
        return eligible
    if n == 0:
        return eligible[:0]
    return eligible[-n:]


def require_lookback_sessions(
    calendar: CalendarLike,
    as_of: date | datetime | pd.Timestamp,
    lookback_sessions: int,
) -> pd.DatetimeIndex:
    """
    Return exactly ``lookback_sessions`` sessions ending at as_of (inclusive).

    Raises ValueError if the calendar cannot satisfy the lookback (caller may
    map this to a feature null_policy later).
    """
    if lookback_sessions < 0:
        msg = "lookback_sessions must be >= 0"
        raise ValueError(msg)
    if lookback_sessions == 0:
        return open_sessions(calendar)[:0]

    window = sessions_on_or_before(calendar, as_of, n=lookback_sessions)
    if len(window) < lookback_sessions:
        msg = (
            f"Insufficient trading sessions for lookback={lookback_sessions} "
            f"as_of={pd.Timestamp(as_of).date().isoformat()} "
            f"(have {len(window)})"
        )
        raise ValueError(msg)
    return window
