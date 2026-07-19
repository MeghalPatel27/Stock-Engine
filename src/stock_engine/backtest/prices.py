"""Load real L1 adjusted prices for backtest fills (fail-closed)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.calendar import open_sessions, session_after
from stock_engine.features.inputs import load_l1_equity_eod, load_open_sessions


def load_l1_price_panel(data_root: Path, as_of_date: date) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """
    Return L1 equity panel with open_adj/close_adj and open calendar.

    Raises if published L1 partition is missing.
    """
    clean = data_root / "clean"
    l1_dir = clean / "l1" / "equity_eod" / f"as_of_date={as_of_date.isoformat()}"
    if not l1_dir.exists():
        msg = f"Published L1 equity missing: {l1_dir}"
        raise FileNotFoundError(msg)
    equity = load_l1_equity_eod(clean, as_of_date)
    calendar = load_open_sessions(clean, as_of_date)
    sessions = open_sessions(calendar)
    required = {"isin", "session_date", "open_adj", "close_adj", "symbol"}
    missing = required - set(equity.columns)
    if missing:
        msg = f"L1 missing columns: {sorted(missing)}"
        raise ValueError(msg)
    if equity.empty:
        msg = "L1 equity panel is empty"
        raise ValueError(msg)
    out = equity[["isin", "symbol", "session_date", "open_adj", "close_adj"]].copy()
    out["isin"] = out["isin"].astype(str)
    out["session_date"] = pd.to_datetime(out["session_date"]).dt.normalize()
    out["open_adj"] = pd.to_numeric(out["open_adj"], errors="coerce")
    out["close_adj"] = pd.to_numeric(out["close_adj"], errors="coerce")
    out = out.dropna(subset=["open_adj", "close_adj"])
    return out, sessions


def holding_period_return(
    prices: pd.DataFrame,
    sessions: pd.DatetimeIndex,
    *,
    isin: str,
    decision_session: pd.Timestamp,
    horizon: int,
) -> float | None:
    """
    Gross return for fill at open(T+1) → exit at open(T+1+H).

    Returns None if either fill is unavailable.
    """
    entry_session = session_after(sessions, decision_session, offset=1)
    if entry_session is None:
        return None
    exit_session = session_after(sessions, entry_session, offset=horizon)
    if exit_session is None:
        return None
    panel = prices.loc[prices["isin"] == isin]
    entry = panel.loc[panel["session_date"] == entry_session, "open_adj"]
    exit_ = panel.loc[panel["session_date"] == exit_session, "open_adj"]
    if entry.empty or exit_.empty:
        return None
    p0 = float(entry.iloc[0])
    p1 = float(exit_.iloc[0])
    if p0 == 0 or not (p0 == p0 and p1 == p1):
        return None
    return p1 / p0 - 1.0
