"""Shared compute context passed to feature computers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd


@dataclass
class ComputeContext:
    """Inputs available while computing a feature set."""

    as_of_date: date
    l1_equity: pd.DataFrame
    open_sessions: pd.DatetimeIndex
    features: dict[str, pd.DataFrame] = field(default_factory=dict)
