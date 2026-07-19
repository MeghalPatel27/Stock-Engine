"""Load published L1 inputs for feature compute."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from stock_engine.features.calendar import open_sessions


def _latest_parquet(folder: Path) -> Path:
    if not folder.exists():
        msg = f"Missing dataset folder: {folder}"
        raise FileNotFoundError(msg)
    files = sorted(folder.glob("*.parquet"))
    if not files:
        msg = f"No parquet files under {folder}"
        raise FileNotFoundError(msg)
    return files[-1]


def load_l1_equity_eod(clean_root: Path, as_of_date: date) -> pd.DataFrame:
    """
    Load L1 equity_eod Parquet published for ``as_of_date``.

    Path: clean/l1/equity_eod/as_of_date=YYYY-MM-DD/*.parquet
    """
    folder = clean_root / "l1" / "equity_eod" / f"as_of_date={as_of_date.isoformat()}"
    return pd.read_parquet(_latest_parquet(folder))


def load_open_sessions(clean_root: Path, as_of_date: date) -> pd.DatetimeIndex:
    """
    Load open sessions from published trading_calendar (L1 preferred, else L0).
    """
    as_of = as_of_date.isoformat()
    candidates = [
        clean_root / "l1" / "trading_calendar" / f"as_of_date={as_of}",
        clean_root / "l0" / "trading_calendar" / f"as_of_date={as_of}",
    ]
    folder = next((p for p in candidates if p.exists()), None)
    if folder is None:
        msg = f"trading_calendar not found for as_of_date={as_of}"
        raise FileNotFoundError(msg)

    cal = pd.read_parquet(_latest_parquet(folder))
    if "session_date" not in cal.columns or "is_open" not in cal.columns:
        msg = "trading_calendar missing session_date/is_open"
        raise ValueError(msg)

    is_open = cal["is_open"]
    if is_open.dtype == object or str(is_open.dtype) == "string":
        mask = is_open.astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        mask = is_open.astype(bool)

    sessions = open_sessions(cal.loc[mask, "session_date"])
    # PIT: calendar days after as_of are unused for feature rows anyway
    cutoff = pd.Timestamp(as_of_date).normalize()
    return sessions[sessions <= cutoff]


def apply_pit_filter(frame: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    """Keep rows with session_date <= as_of_date (normalized)."""
    if "session_date" not in frame.columns:
        msg = "frame missing session_date"
        raise ValueError(msg)
    out = frame.copy()
    out["session_date"] = pd.to_datetime(out["session_date"]).dt.normalize()
    cutoff = pd.Timestamp(as_of_date).normalize()
    return out.loc[out["session_date"] <= cutoff].reset_index(drop=True)
