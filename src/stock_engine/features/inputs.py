"""Load published L1 inputs for feature compute."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


def load_l1_equity_eod(clean_root: Path, as_of_date: date) -> pd.DataFrame:
    """
    Load L1 equity_eod Parquet published for ``as_of_date``.

    Path: clean/l1/equity_eod/as_of_date=YYYY-MM-DD/*.parquet
    """
    folder = clean_root / "l1" / "equity_eod" / f"as_of_date={as_of_date.isoformat()}"
    if not folder.exists():
        msg = f"L1 equity_eod not found for as_of_date={as_of_date.isoformat()}: {folder}"
        raise FileNotFoundError(msg)
    files = sorted(folder.glob("*.parquet"))
    if not files:
        msg = f"No L1 equity_eod parquet under {folder}"
        raise FileNotFoundError(msg)
    # Deterministic: last sorted name if multiple versions present
    return pd.read_parquet(files[-1])


def apply_pit_filter(frame: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
    """Keep rows with session_date <= as_of_date (normalized)."""
    if "session_date" not in frame.columns:
        msg = "frame missing session_date"
        raise ValueError(msg)
    out = frame.copy()
    out["session_date"] = pd.to_datetime(out["session_date"]).dt.normalize()
    cutoff = pd.Timestamp(as_of_date).normalize()
    return out.loc[out["session_date"] <= cutoff].reset_index(drop=True)
